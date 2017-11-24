import os
from threading import Lock
from collections import namedtuple


FileChunk = namedtuple('FileChunk', ['index', 'size', 'read'])


def build_chunks(read_bytes, file_size, chunk_size):

    chunks = []

    index = 0
    start = 0

    while start < file_size:
        end = min(start + chunk_size, file_size)
        size = end - start

        chunk = FileChunk(index, size, lambda: read_bytes(start, size))
        chunks.append(chunk)

        index += 1
        start += chunk_size

    return chunks


class LazyLoadChunkableFile(object):

    def __init__(self, path, chunk_size):
        self.path = str(path)
        self.chunk_size = int(chunk_size)

        self.size = os.path.getsize(self.path)

        self._fp = open(self.path, 'rb')
        self._fp_lock = Lock()

        self.chunks = build_chunks(self._read_bytes, self.size, chunk_size)

    def close(self):
        self._fp.close()

    def _read_bytes(self, start, num_bytes):
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(num_bytes)
