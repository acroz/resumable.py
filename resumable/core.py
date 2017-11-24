import os
from enum import Enum
import uuid
import mimetypes
from concurrent.futures import ThreadPoolExecutor

import requests

from resumable.file import LazyLoadChunkableFile
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

        self.executor = ThreadPoolExecutor(simultaneous_uploads)

    def add_file(self, path):
        lazy_load_file = LazyLoadChunkableFile(path, self.config.chunk_size)
        file = ResumableFile(lazy_load_file)
        self.files.append(file)
        self.send_signal(ResumableSignal.FILE_ADDED)
        file.proxy_signals_to(self)

        for chunk in lazy_load_file.chunks:
            self.executor.submit(
                _resolve_chunk,
                self.session, self.config, file, chunk
            )

        return file

    def close(self):
        for file in self.files:
            file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.executor.shutdown()
        self.close()


def _file_type(file):
    """Mimic the type parameter of a JS File object.

    Resumable.js uses the File object's type attribute to guess mime type,
    which is guessed from file extention accoring to
    https://developer.mozilla.org/en-US/docs/Web/API/File/type.
    """
    type_, _ = mimetypes.guess_type(file.file.path)
    # When no type can be inferred, File.type returns an empty string
    return '' if type_ is None else type_


def _build_query(file, chunk):
    return {
        'resumableChunkSize': file.file.chunk_size,
        'resumableTotalSize': file.file.size,
        'resumableType': _file_type(file),
        'resumableIdentifier': str(file.unique_identifier),
        'resumableFilename': os.path.basename(file.file.path),
        'resumableRelativePath': file.file.path,
        'resumableTotalChunks': len(file.file.chunks),
        'resumableChunkNumber': chunk.index + 1,
        'resumableCurrentChunkSize': chunk.size
    }


def _test_chunk(session, config, file, chunk):
    response = session.get(
        config.target,
        data=_build_query(file, chunk)
    )
    return response.status_code == 200


def _send_chunk(session, config, file, chunk):
    response = session.post(
        config.target,
        data=_build_query(file, chunk),
        files={'file': chunk.data}
    )
    if response.status_code in config.permanent_errors:
        # TODO: better exception
        raise RuntimeError('permanent error')
    return response.status_code in [200, 201]


def _resolve_chunk(session, config, file, chunk):
    if config.test_chunks and _test_chunk(session, config, file, chunk):
        return
    tries = 0
    while not _send_chunk(session, config, file, chunk):
        tries += 1
        if tries >= config.max_chunk_retries:
            raise RuntimeError('max retries exceeded')
    file.chunk_done[chunk] = True


class ResumableFile(CallbackMixin):

    def __init__(self, file):
        super(ResumableFile, self).__init__()

        self.file = file
        self.unique_identifier = uuid.uuid4()

        self.chunk_done = {chunk: False for chunk in self.file.chunks}

    def close(self):
        self.file.close()

    @property
    def completed(self):
        return all(self.chunk_done.values())

    def handle_chunk_completion(self):
        if self.completed:
            self.send_signal(ResumableSignal.FILE_COMPLETED)
            self.close()
