import os
from threading import Lock


class LazyLoadChunkableFile(object):

    def __init__(self, path, chunk_size):
        self.path = str(path)
        self.chunk_size = int(chunk_size)

        self.size = os.path.getsize(self.path)

        self._fp = open(self.path, 'rb')
        self._fp_lock = Lock()

        self._chunks = None

    def close(self):
        self._fp.close()

    def read_bytes(self, start, num_bytes):
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(num_bytes)

    @property
    def chunks(self):
        if self._chunks is not None:
            return self._chunks
        self._chunks = []
        index = 0
        start = 0
        while start < self.size:
            end = min(start + self.chunk_size, self.size)
            chunk = LazyLoadFileChunk(self, index, start, end - start)
            self._chunks.append(chunk)
            index += 1
            start += self.chunk_size
        return self._chunks


class LazyLoadFileChunk(object):

    def __init__(self, file, index, start, size):
        self._file = file
        self.index = index
        self._start = start
        self.size = size

    @property
    def data(self):
        return self._file.read_bytes(self._start, self.size)
