import os
from enum import Enum
import uuid
from collections import defaultdict
import mimetypes

import requests

from resumable.file import LazyLoadChunkableFile
from resumable.worker import ResumableWorkerPool


MB = 1024 * 1024


class ResumableSignal(Enum):
    CHUNK_COMPLETED = 0
    FILE_ADDED = 1
    FILE_COMPLETED = 2


class CallbackMixin(object):

    def __init__(self, *args, **kwargs):
        super(CallbackMixin, self).__init__(*args, **kwargs)
        self.signal_callbacks = defaultdict(list)
        self.signal_proxy_targets = []

    def register_callback(self, signal, callback):
        self.signal_callbacks[signal].append(callback)

    def proxy_signals_to(self, target):
        self.signal_proxy_targets.append(target)

    def send_signal(self, signal):
        for callback in self.signal_callbacks[signal]:
            callback()
        for target in self.signal_proxy_targets:
            target.send_signal(signal)


class Resumable(CallbackMixin):

    def __init__(self, target, simultaneous_uploads=3, chunk_size=MB,
                 headers=None):
        super(Resumable, self).__init__()
        self.target = target
        self.chunk_size = chunk_size
        self.headers = headers

        self.files = []

        self.worker_pool = ResumableWorkerPool(simultaneous_uploads,
                                               self.next_task)

    def add_file(self, path):
        file = ResumableFile(path, self.chunk_size)
        self.files.append(file)
        self.send_signal(ResumableSignal.FILE_ADDED)
        file.proxy_signals_to(self)

    def wait_until_complete(self):
        self.worker_pool.join()

    def close(self):
        for file in self.files:
            file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.wait_until_complete()
        self.close()

    @property
    def chunks(self):
        for file in self.files:
            yield from file.chunks

    def next_task(self):
        for chunk in self.chunks:
            if chunk.state == ResumableChunkState.QUEUED:
                return chunk.create_task(self.target, self.headers)


class ResumableFile(CallbackMixin):

    def __init__(self, path, chunk_size):
        super(ResumableFile, self).__init__()

        self.file = LazyLoadChunkableFile(path, chunk_size)
        self.unique_identifier = uuid.uuid4()

        self.chunks = [ResumableChunk(self, chunk)
                       for chunk in self.file.chunks]

        for chunk in self.chunks:
            chunk.proxy_signals_to(self)
            chunk.register_callback(ResumableSignal.CHUNK_COMPLETED,
                                    self.handle_chunk_completion)

    def close(self):
        self.file.close()

    @property
    def type(self):
        """Mimic the type parameter of a JS File object.

        Resumable.js uses the File object's type attribute to guess mime type,
        which is guessed from file extention accoring to
        https://developer.mozilla.org/en-US/docs/Web/API/File/type.
        """
        type_, _ = mimetypes.guess_type(self.file.path)
        # When no type can be inferred, File.type returns an empty string
        return '' if type_ is None else type_

    @property
    def query(self):
        return {
            'resumableChunkSize': self.file.chunk_size,
            'resumableTotalSize': self.file.size,
            'resumableType': self.type,
            'resumableIdentifier': str(self.unique_identifier),
            'resumableFileName': os.path.basename(self.file.path),
            'resumableRelativePath': self.file.path,
            'resumableTotalChunks': len(self.chunks)
        }

    @property
    def completed(self):
        for chunk in self.chunks:
            if chunk.state != ResumableChunkState.DONE:
                return False
        else:
            return True

    def handle_chunk_completion(self):
        if self.completed:
            self.send_signal(ResumableSignal.FILE_COMPLETED)
            self.file.close()


class ResumableChunkState(Enum):
    QUEUED = 0
    POPPED = 1
    UPLOADING = 2
    DONE = 3


class ResumableChunk(CallbackMixin):

    def __init__(self, file, chunk):
        super(ResumableChunk, self).__init__()
        self.file = file
        self.chunk = chunk
        self.state = ResumableChunkState.QUEUED

    @property
    def query(self):
        query = {
            'resumableChunkNumber': self.chunk.index + 1,
            'resumableCurrentChunkSize': self.chunk.size
        }
        query.update(self.file.query)
        return query

    def test(self, target, headers=None):
        response = requests.get(target, headers=headers, data=self.query)
        if response.status_code == 200:
            self.state = ResumableChunkState.DONE
            self.send_signal(ResumableSignal.CHUNK_COMPLETED)

    def send(self, target, headers=None):
        self.state = ResumableChunkState.UPLOADING
        response = requests.post(target, headers=headers, data=self.query,
                                 files={'file': self.chunk.data})
        response.raise_for_status()
        self.state = ResumableChunkState.DONE
        self.send_signal(ResumableSignal.CHUNK_COMPLETED)

    def create_task(self, target, headers=None):
        def task():
            self.test(target, headers)
            if self.state != ResumableChunkState.DONE:
                self.send(target, headers)
        self.state = ResumableChunkState.POPPED
        return task
