from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

import requests

from resumable.version import user_agent
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
    chunk_size : int, optional
        The size, in bytes, of file chunks to be uploaded
    simultaneous_uploads : int, optional
        The number of file chunk uploads to attempt at once
    headers : dict, optional
        A dictionary of additional HTTP headers to include in requests
    test_chunks : bool
        Flag indicating if the client should check with the server if a chunk
        already exists with a GET request prior to attempting to upload the
        chunk with a POST
    max_chunk_retries : int, optional
        The number of times to retry uploading a chunk
    permanent_errors : collection of int, optional
        HTTP status codes that indicate the upload of a chunk has failed and
        should not be retried

    Attributes
    ----------
    file_added : resumable.util.CallbackDispatcher
        Triggered when a file has been added, passing the file object
    file_completed : resumable.util.CallbackDispatcher
        Triggered when a file upload has completed, passing the file object
    chunk_completed : resumable.util.CallbackDispatcher
        Triggered when a chunk upload has completed, passing the file and chunk
        objects
    """

    def __init__(self, target, chunk_size=MiB, simultaneous_uploads=3,
                 headers=None, test_chunks=True,
                 max_chunk_retries=100,
                 permanent_errors=(400, 404, 415, 500, 501)):

        self.config = Config(
            target=target,
            chunk_size=chunk_size,
            simultaneous_uploads=simultaneous_uploads,
            headers=headers,
            test_chunks=test_chunks,
            max_chunk_retries=max_chunk_retries,
            permanent_errors=permanent_errors
        )

        self.session = requests.Session()
        self.session.headers['User-Agent'] = user_agent()
        if headers:
            self.session.headers.update(headers)

        self.files = []

        self.executor = ThreadPoolExecutor(simultaneous_uploads)
        self.futures = []

        self.file_added = CallbackDispatcher()
        self.file_completed = CallbackDispatcher()
        self.chunk_completed = CallbackDispatcher()

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
        file.completed.register(partial(self.file_completed.trigger, file))
        file.chunk_completed.register(
            partial(self.chunk_completed.trigger, file)
        )

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
