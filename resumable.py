import os
from enum import Enum
import uuid
import math
from collections import defaultdict
from threading import Thread, Lock
import time

import requests


MB = 1024 * 1024


class ResumableSignal(Enum):
    CHUNK_COMPLETED = 0
    FILE_ADDED = 1
    FILE_COMPLETED = 2


NEXT_TASK_LOCK = Lock()


class ResumableWorkerPool(object):

    def __init__(self, num_workers, get_task):
        self.workers = [ResumableWorker(get_task) for _ in range(num_workers)]
        for worker in self.workers:
            worker.start()

    def join(self):
        for worker in self.workers:
            worker.poll = False
        for worker in self.workers:
            worker.join()


class ResumableWorker(Thread):

    def __init__(self, get_task, poll=True):
        super(ResumableWorker, self).__init__()
        self.get_task = get_task
        self.poll = poll

    def run(self):
        while True:
            with NEXT_TASK_LOCK:
                task = self.get_task()
            while task:
                task()
                with NEXT_TASK_LOCK:
                    task = self.get_task()
            if self.poll:
                time.sleep(0.1)
            else:
                break


class Resumable(object):

    def __init__(self, target, simultaneous_uploads=3, chunk_size=MB,
                 headers=None):
        self.target = target
        self.chunk_size = chunk_size
        self.headers = headers

        self.files = []
        self.signal_callbacks = defaultdict(list)

        self.worker_pool = ResumableWorkerPool(simultaneous_uploads,
                                               self.next_task)

    def add_file(self, path):
        file = ResumableFile(path, self.chunk_size)
        self.files.append(file)
        self.send_signal(ResumableSignal.FILE_ADDED, file)

    def register_callback(self, signal, callback):
        self.signal_callbacks[signal].append(callback)

    def send_signal(self, signal, *args):
        for callback in self.signal_callbacks[signal]:
            callback(*args)

    def wait_until_complete(self):
        self.worker_pool.join()

    def close(self):
        for file in self.files:
            file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.wait_until_complete()
        self.close()

    @property
    def queued_chunks(self):
        for file in self.files:
            yield from file.queued_chunks

    def next_task(self):
        try:
            next_chunk = next(self.queued_chunks)
        except StopIteration:
            return None
        else:
            return lambda: next_chunk.send(self.target, self.headers)


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

    @property
    def queued_chunks(self):
        for chunk in self.chunks:
            if chunk.state == ResumableChunkState.QUEUED:
                yield chunk


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
