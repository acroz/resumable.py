import os
from enum import Enum
import uuid
import math
from collections import defaultdict
from threading import Lock

import requests

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
        self.path = path
        self.chunk_size = chunk_size

        self.size = os.path.getsize(path)
        self._fp = open(path, 'rb')
        self._fp_lock = Lock()
        self.unique_identifier = uuid.uuid4()

        n_chunks = math.ceil(self.size / float(self.chunk_size))
        self.chunks = [ResumableChunk(self, i) for i in range(n_chunks)]
        for chunk in self.chunks:
            chunk.proxy_signals_to(self)
            chunk.register_callback(ResumableChunk.CHUNK_COMPLETED,
                                    self.handle_chunk_completion)

    @property
    def name(self):
        return os.path.basename(self.path)

    def close(self):
        self._fp.close()

    def load_bytes(self, start, size):
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(size)

    @property
    def completed(self):
        for chunk in self.chunks:
            if chunk.state != ResumableChunkState.DONE:
                return False
        else:
            return True

    def handle_chunk_completion(self):
        if self.completed:
            self.send_signal(ResumableSignal.FILE_COMPLETED, self)
            self.close()


class ResumableChunkState(Enum):
    QUEUED = 0
    POPPED = 1
    UPLOADING = 2
    DONE = 3


class ResumableChunk(CallbackMixin):

    def __init__(self, file, chunk_index):
        self.file = file
        self.chunk_index = chunk_index
        self.state = ResumableChunkState.QUEUED

    @property
    def start(self):
        return self.chunk_index * self.file.chunk_size

    def load(self):
        return self.file.load_bytes(self.start, self.file.chunk_size)

    def _query(self, chunk_data):
        return {
            'resumableChunkNumber': self.chunk_index + 1,
            'resumableChunkSize': self.file.chunk_size,
            'resumableCurrentChunkSize': len(chunk_data),
            'resumableTotalSize': self.file.size,
            # 'resumableType': '', TODO: guess mime type?
            'resumableIdentifier': str(self.file.unique_identifier),
            'resumableFileName': self.file.name,
            'resumableRelativePath': self.file.path,
            'resumableTotalChunks': len(self.file.chunks)
        }

    def test(self, target, headers=None):
        chunk_data = self.load()
        response = requests.get(target, headers=headers,
                                data=self._query(chunk_data))
        if response.status_code == 200:
            self.state = ResumableChunkState.DONE
            self.send_signal(ResumableSignal.CHUNK_COMPLETED, self)

    def send(self, target, headers=None):
        self.state = ResumableChunkState.UPLOADING
        chunk_data = self.load()
        response = requests.post(target, headers=headers,
                                 data=self._query(chunk_data),
                                 files={'file': chunk_data})
        response.raise_for_status()
        self.state = ResumableChunkState.DONE
        self.send_signal(ResumableSignal.CHUNK_COMPLETED, self)

    def create_task(self, target, headers=None):
        def task():
            self.test(target, headers)
            if self.state != ResumableChunkState.DONE:
                self.send(target, headers)
        self.state = ResumableChunkState.POPPED
        return task
