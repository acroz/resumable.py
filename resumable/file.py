from __future__ import division

import os
import uuid
from threading import Lock
from collections import namedtuple
from functools import partial

from resumable.util import CallbackDispatcher


FileChunk = namedtuple('FileChunk', ['index', 'size', 'read'])


def build_chunks(read_bytes, file_size, chunk_size):
    """Build a sequence of chunks from a file.

    Parameters
    ----------
    read_bytes : callable
        A callable returning the data for a byte range of a file
    file_size : int
        The total size of the file, in bytes
    chunk_size : int
        The size of the generated chunks, in bytes

    Returns
    -------
    list of resumable.file.FileChunk
    """

    chunks = []

    index = 0
    start = 0

    while start < file_size:
        end = min(start + chunk_size, file_size)
        size = end - start

        chunk = FileChunk(index, size, partial(read_bytes, start, size))
        chunks.append(chunk)

        index += 1
        start += chunk_size

    return chunks


class ResumableFile(object):
    """A file to be uploaded in a resumable session.

    Parameters
    ----------
    path : str or pathlib.Path
        The path of the file
    chunk_size : int
        The size, in bytes, of chunks uploaded in a single request

    Attributes
    ----------
    completed : resumable.util.CallbackDispatcher
        Triggered when all chunks of the file have been uploaded
    chunk_completed : resumable.util.CallbackDispatcher
        Triggered when a chunks of the file has been uploaded, passing the
        chunk
    """

    def __init__(self, path, chunk_size):

        self.path = str(path)
        self.unique_identifier = uuid.uuid4()
        self.chunk_size = int(chunk_size)
        self.size = os.path.getsize(self.path)

        self._fp = open(self.path, 'rb')
        self._fp_lock = Lock()

        self.chunks = build_chunks(self._read_bytes, self.size, chunk_size)
        self._chunk_done = {chunk: False for chunk in self.chunks}

        self.completed = CallbackDispatcher()
        self.chunk_completed = CallbackDispatcher()

    def close(self):
        """Close the file."""
        self._fp.close()

    def _read_bytes(self, start, num_bytes):
        """Read a byte range from the file."""
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(num_bytes)

    @property
    def is_completed(self):
        """Indicates if all chunks of this file have been uploaded."""
        return all(self._chunk_done.values())

    @property
    def fraction_completed(self):
        """The fraction of the file that has been completed."""
        return sum(self._chunk_done.values()) / len(self.chunks)

    def mark_chunk_completed(self, chunk):
        """Mark a chunk of this file as having been successfully uploaded.

        If all chunks have been completed, this will trigger the `completed`
        callback of this file.

        Parameters
        ----------
        chunk : resumable.chunk.FileChunk
            The chunk to mark as completed
        """
        self._chunk_done[chunk] = True
        if self.is_completed:
            self.completed.trigger()
            self.close()
        self.chunk_completed.trigger(chunk)
