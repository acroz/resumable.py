import os
import uuid
from threading import Lock
from collections import namedtuple
from functools import partial

from resumable.util import CallbackDispatcher


FileChunk = namedtuple('FileChunk', ['index', 'size', 'read'])


def build_chunks(read_bytes, file_size, chunk_size):

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

    def __init__(self, path, chunk_size):

        self.path = str(path)
        self.unique_identifier = uuid.uuid4()
        self.chunk_size = int(chunk_size)
        self.size = os.path.getsize(path)

        self._fp = open(path, 'rb')
        self._fp_lock = Lock()

        self.chunks = build_chunks(self._read_bytes, self.size, chunk_size)
        self._chunk_done = {chunk: False for chunk in self.chunks}

        self.completed = CallbackDispatcher()

    def close(self):
        self._fp.close()

    def _read_bytes(self, start, num_bytes):
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(num_bytes)

    @property
    def is_completed(self):
        return all(self._chunk_done.values())

    def mark_chunk_completed(self, chunk):
        self._chunk_done[chunk] = True
        if self.is_completed:
            self.completed.trigger()
            self.close()
