import time
from threading import Thread, Lock


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
