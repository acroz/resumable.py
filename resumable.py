import os
from enum import Enum
import uuid
import math

import requests


MB = 1024 * 1024


class Resumable(object):

    def __init__(self, target, chunk_size=MB, headers=None):
        self.target = target
        self.chunk_size = chunk_size
        self.headers = headers

        self.files = []

    def add_file(self, path):
        self.files.append(ResumableFile(path, self.chunk_size))

    def close(self):
        for file in self.files:
            file.close()

    def upload(self):
        for file in self.files:
            chunk = file.next_queued_chunk()
            while chunk:
                chunk.send(self.target, self.headers)
                chunk = file.next_queued_chunk()


class ResumableFile(object):

    def __init__(self, path, chunk_size):
        self.path = path
        self.chunk_size = chunk_size

        self.size = os.path.getsize(path)
        self._fp = open(path, 'rb')
        self.unique_identifier = uuid.uuid4()

        n_chunks = math.ceil(self.size / float(self.chunk_size))
        self.chunks = [ResumableChunk(self, i) for i in range(n_chunks)]

    @property
    def name(self):
        return os.path.basename(self.path)

    def close(self):
        self._fp.close()

    def load_bytes(self, start, size):
        # TODO: Lock when async
        self._fp.seek(start)
        return self._fp.read(size)

    def next_queued_chunk(self):
        for chunk in self.chunks:
            if chunk.state == ResumableChunkState.QUEUED:
                return chunk


class ResumableChunkState(Enum):
    QUEUED = 0
    UPLOADING = 1
    DONE = 2


class ResumableChunk(object):

    def __init__(self, file, chunk_index):
        self.file = file
        self.chunk_index = chunk_index
        self.state = ResumableChunkState.QUEUED

    @property
    def start(self):
        return self.chunk_index * self.file.chunk_size

    def load(self):
        return self.file.load_bytes(self.start, self.file.chunk_size)

    def send(self, target, headers=None):

        self.state = ResumableChunkState.UPLOADING

        chunk_data = self.load()

        query = {
            'resumableChunkNumber': self.chunk_index + 1,
            'resumableChunkSize': self.file.chunk_size,
            'resumableCurrentChunkSize': len(chunk_data),
            'resumableTotalSize': self.file.size,
            #'resumableType': '', TODO: guess mime type?
            'resumableIdentifier': str(self.file.unique_identifier),
            'resumableFileName': self.file.name,
            'resumableRelativePath': self.file.path,
            'resumableTotalChunks': len(self.file.chunks)
        }

        response = requests.post(target, headers=headers, data=query,
                                 files={'file': chunk_data})
        response.raise_for_status()

        self.state = ResumableChunkState.DONE
