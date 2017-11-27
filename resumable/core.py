import os
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from resumable.file import ResumableFile
from resumable.util import CallbackDispatcher, Config


MB = 1024 * 1024


class Resumable(object):

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
        self.futures = []

        self.file_added = CallbackDispatcher()
        self.file_completed = CallbackDispatcher()

    def add_file(self, path):
        file = ResumableFile(path, self.config.chunk_size)
        self.files.append(file)

        self.file_added.trigger(file)
        file.completed.register(lambda: self.file_completed.trigger(file))

        for chunk in file.chunks:
            future = self.executor.submit(
                _resolve_chunk,
                self.session, self.config, file, chunk
            )
            self.futures.append(future)

        return file

    def join(self):
        """Wait until all current uploads are completed."""
        for future in as_completed(self.futures):
            if future.exception():
                raise future.exception()

    def _cancel_remaining_futures(self):
        for future in self.futures:
            if not future.done():
                future.cancel()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.join()
        except:  # noqa: E722
            self._cancel_remaining_futures()
            raise
        finally:
            self.executor.shutdown()
            for file in self.files:
                file.close()


def _file_type(path):
    """Mimic the type parameter of a JS File object.

    Resumable.js uses the File object's type attribute to guess mime type,
    which is guessed from file extention accoring to
    https://developer.mozilla.org/en-US/docs/Web/API/File/type.
    """
    type_, _ = mimetypes.guess_type(path)
    # When no type can be inferred, File.type returns an empty string
    return '' if type_ is None else type_


def _build_query(file, chunk):
    return {
        'resumableChunkSize': file.chunk_size,
        'resumableTotalSize': file.size,
        'resumableType': _file_type(file.path),
        'resumableIdentifier': str(file.unique_identifier),
        'resumableFilename': os.path.basename(file.path),
        'resumableRelativePath': file.path,
        'resumableTotalChunks': len(file.chunks),
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
        files={'file': chunk.read()}
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
