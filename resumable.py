import os
import uuid
import requests


MB = 1024 * 1024


class Resumable(object):

    def __init__(self, target, chunk_size=MB, file_parameter_name='file',
                 headers=None):
        self.target = target
        self.chunk_size = chunk_size
        self.file_parameter_name = file_parameter_name
        self.headers = headers or {}


class ResumableFile(object):

    def __init__(self, path, chunk_size):
        self.path = path
        self.chunk_size = chunk_size

        self.size = os.path.getsize(path)
        self._fp = open(path, 'rb')
        self.unique_identifier = uuid.uuid4()

    @property
    def name(self):
        return os.path.basename(self.path)

    def close(self):
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def load_slice(self, start, size):
        # TODO: Lock when async
        self._fp.seek(start)
        return self._fp.read(size)


class ResumableChunk(object):

    def __init__(self, file, chunk_index, chunk_size):
        self.file = file
        self.chunk_index = chunk_index

    @property
    def start(self):
        return self.chunk_index * self.file.chunk_size

    def load(self):
        return self.file.load_bytes(self.start, self.file.chunk_size)

    def send(self, target):
        data = self.load()
        query = {
            'chunkNumberParameterName': self.chunk_index + 1,
            'chunkSizeParameterName': self.file.chunk_size,
            'currentChunkSizeParameterName': len(data),
            'totalSizeParameterName': self.file.size,
            #'typeParameterName': '', TODO: guess mime type?
            'identifierParameterName': str(self.file.unique_identifier),
            'fileNameParameterName': self.file.name,
            'relativePathParameterName': self.file.path,
            'totalChunksParameterName': 0  #TODO: number of chunks
        }
        response = requests.post(
            target,
            data=query,
            files={self.file.name: data}
        )
        response.raise_for_status()
