from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from resumable.file import ResumableFile
from resumable.chunk import resolve_chunk
from resumable.util import CallbackDispatcher, Config


MiB = 1024 * 1024


class Resumable(object):
    """A resumable.py upload client.

    Parameters
    ----------
    target : str
        The URL of the resumable upload target
    simultaneous_uploads : int, optional
        The number of file chunk uploads to attempt at once
    chunk_size : int, optional
        The size, in bytes, of file chunks to be uploaded
    headers : dict, optional
        A dictionary of additional HTTP headers to include in requests
    max_chunk_retries : int, optional
        The number of times to retry uploading a chunk
    permanent_errors : collection of int, optional
        HTTP status codes that indicate the upload of a chunk has failed and
        should not be retried
    test_chunks : bool
        Flag indicating if the client should check with the server if a chunk
        already exists with a GET request prior to attempting to upload the
        chunk with a POST

    Attributes
    ----------
    file_added : resumable.util.CallbackDispatcher
        Triggered when a file has been added, passing the file object
    file_completed : resumable.util.CallbackDispatcher
        Triggered when a file upload has completed, passing the file object
    """

    def __init__(self, target, simultaneous_uploads=3, chunk_size=MiB,
                 headers=None, max_chunk_retries=100,
                 permanent_errors=(400, 404, 415, 500, 501), test_chunks=True):

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
        """Add a file to be uploaded.

        Parameters
        ----------
        path : str
            The file of the path to be uploaded

        Returns
        -------
        resumable.file.ResumableFile
        """

        file = ResumableFile(path, self.config.chunk_size)
        self.files.append(file)

        self.file_added.trigger(file)
        file.completed.register(lambda: self.file_completed.trigger(file))

        for chunk in file.chunks:
            future = self.executor.submit(
                resolve_chunk, self.session, self.config, file, chunk
            )
            self.futures.append(future)

        return file

    def _wait(self):
        """Wait until all current uploads are completed."""
        for future in as_completed(self.futures):
            if future.exception():
                raise future.exception()

    def _cancel_remaining_futures(self):
        for future in self.futures:
            if not future.done():
                future.cancel()

    def join(self):
        """Block until all uploads are complete, or an error occurs."""
        try:
            self._wait()
        except:  # noqa: E722
            self._cancel_remaining_futures()
            raise
        finally:
            self.executor.shutdown()
            for file in self.files:
                file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.join()
