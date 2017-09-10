import os
from enum import Enum
import uuid
import mimetypes

import requests

from resumable.file import LazyLoadChunkableFile
from resumable.worker import ResumableWorkerPool
from resumable.util import CallbackMixin, Config


MB = 1024 * 1024


class ResumableSignal(Enum):
    FILE_ADDED = 0
    FILE_COMPLETED = 1
    CHUNK_COMPLETED = 2
    CHUNK_RETRY = 3
    CHUNK_FAILED = 4


class Resumable(CallbackMixin):

    def __init__(self, target, simultaneous_uploads=3, chunk_size=MB,
                 headers=None, max_chunk_retries=100,
                 permanent_errors=[400, 404, 415, 500, 501], test_chunks=True):
        super(Resumable, self).__init__()

        self.config = Config(
            target=target,
            headers=headers,
            simultaneous_uploads=simultaneous_uploads,
            chunk_size=chunk_size,
            max_chunk_retries=max_chunk_retries,
            permanent_errors=permanent_errors,
            test_chunks=test_chunks
        )

        self.session = requests.Session()

        # TODO: Set User-Agent as python-resumable/version
        if headers:
            self.session.headers.update(headers)

        self.files = []

        self.worker_pool = ResumableWorkerPool(simultaneous_uploads,
                                               self.next_task)

    def add_file(self, path):
        lazy_load_file = LazyLoadChunkableFile(path, self.config.chunk_size)
        file = ResumableFile(self.session, self.config, lazy_load_file)
        self.files.append(file)
        self.send_signal(ResumableSignal.FILE_ADDED)
        file.proxy_signals_to(self)
        return file

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
            for chunk in file.chunks:
                yield chunk

    def next_task(self):
        for chunk in self.chunks:
            if chunk.status == ResumableChunkState.PENDING:
                return chunk.create_task()


class ResumableFile(CallbackMixin):

    def __init__(self, session, config, file):
        super(ResumableFile, self).__init__()

        self.config = config
        self.file = file
        self.unique_identifier = uuid.uuid4()

        self.chunks = [ResumableChunk(session, self.config, self, chunk)
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
            if chunk.status != ResumableChunkState.SUCCESS:
                return False
        else:
            return True

    def handle_chunk_completion(self):
        if self.completed:
            self.send_signal(ResumableSignal.FILE_COMPLETED)
            self.close()


class ResumableChunkState(Enum):
    PENDING = 0
    POPPED = 1
    UPLOADING = 2
    SUCCESS = 3
    ERROR = 4


class ResumableChunk(CallbackMixin):

    def __init__(self, session, config, file, chunk):
        super(ResumableChunk, self).__init__()
        self.session = session
        self.config = config
        self.file = file
        self.chunk = chunk
        self.status = ResumableChunkState.PENDING
        self.tested = False
        self.retries = 0

    def __eq__(self, other):
        return (isinstance(other, ResumableChunk) and
                self.session == other.session and
                self.config == other.config and
                self.file == other.file and
                self.chunk == other.chunk and
                self.status == other.status and
                self.tested == other.tested and
                self.retries == other.retries)

    @property
    def query(self):
        query = {
            'resumableChunkNumber': self.chunk.index + 1,
            'resumableCurrentChunkSize': self.chunk.size
        }
        query.update(self.file.query)
        return query

    def test(self):
        response = self.session.get(
            self.config.target,
            data=self.query
        )
        if response.status_code == 200:
            self.status = ResumableChunkState.SUCCESS
            self.send_signal(ResumableSignal.CHUNK_COMPLETED)
        self.tested = True

    def send(self):
        self.status = ResumableChunkState.UPLOADING
        response = self.session.post(
            self.config.target,
            data=self.query,
            files={'file': self.chunk.data}
        )
        if response.status_code in [200, 201]:
            self.status = ResumableChunkState.SUCCESS
            self.send_signal(ResumableSignal.CHUNK_COMPLETED)
        elif (response.status_code in self.config.permanent_errors or
              self.retries >= self.config.max_chunk_retries):
            self.status = ResumableChunkState.ERROR
            self.send_signal(ResumableSignal.CHUNK_FAILED)
        else:
            self.retries += 1
            self.status = ResumableChunkState.PENDING
            self.send_signal(ResumableSignal.CHUNK_RETRY)

    def resolve(self):
        if self.config.test_chunks and not self.tested:
            self.test()
        if self.status != ResumableChunkState.SUCCESS:
            self.send()

    def create_task(self):
        self.status = ResumableChunkState.POPPED
        return self.resolve
