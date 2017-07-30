import os
from threading import Lock


class LazyLoadChunkableFile(object):

    def __init__(self, path, chunk_size):
        self.path = path
        self.chunk_size = chunk_size

        self.size = os.path.getsize(path)

        self._fp = open(path, 'rb')
        self._fp_lock = Lock()

    def close(self):
        self._fp.close()

    def read_bytes(self, start, num_bytes):
        with self._fp_lock:
            self._fp.seek(start)
            return self._fp.read(num_bytes)

    @property
    def chunks(self):
        index = 0
        start = 0
        while start < self.size:
            end = min(start + self.chunk_size, self.size)
            yield LazyLoadFileChunk(self, index, start, end - start)
            index += 1
            start += self.chunk_size


class LazyLoadFileChunk(object):

    def __init__(self, file, index, start, size):
        self._file = file
        self.index = index
        self._start = start
        self.size = size

    @property
    def data(self):
        return self._file.read_bytes(self._start, self.size)
