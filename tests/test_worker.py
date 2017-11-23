import time
from threading import Event

from mock import Mock

from resumable.worker import (
    ResumableWorkerPool, ResumableWorker, NEXT_TASK_LOCK
)


class GetTaskMock(Mock):

    def __init__(self, tasks=None, next_task_block=None):
        super(GetTaskMock, self).__init__(side_effect=self.next_task)
        self.tasks = tasks or []
        self.position = 0
        self.next_task_block = next_task_block

    def append_task(self, task):
        self.tasks.append(task)

    def next_task(self):
        if self.next_task_block:
            self.next_task_block.wait()
        try:
            task = self.tasks[self.position]
        except IndexError:
            task = None
        else:
            self.position += 1
        return task

    def assert_no_tasks_called(self):
        for task in self.tasks:
            task.assert_not_called()

    def assert_all_tasks_called(self):
        for task in self.tasks:
            task.assert_called_once()


def test_worker():
    get_task = GetTaskMock([Mock(), Mock()])
    worker = ResumableWorker(get_task, poll=False)
    worker.start()
    worker.join()
    get_task.assert_all_tasks_called()


def test_worker_polling():
    get_task = GetTaskMock([Mock(), Mock()])
    worker = ResumableWorker(get_task, poll=True)
    worker.start()

    worker.join(timeout=0.2)
    assert worker.is_alive()
    get_task.assert_all_tasks_called()

    get_task.append_task(Mock())
    get_task.append_task(Mock())
    worker.poll = False
    worker.join()
    get_task.assert_all_tasks_called()


def test_worker_acquires_next_task_lock():
    next_task_block = Event()

    get_task = GetTaskMock([Mock(), Mock()], next_task_block)
    worker = ResumableWorker(get_task, poll=False)
    worker.start()
    worker.join(timeout=0.1)

    assert NEXT_TASK_LOCK.locked()

    next_task_block.set()
    worker.join()

    assert not NEXT_TASK_LOCK.locked()


def test_worker_respects_next_task_lock():
    get_task = GetTaskMock([Mock(), Mock()])
    worker = ResumableWorker(get_task, poll=False)

    NEXT_TASK_LOCK.acquire()
    worker.start()
    worker.join(timeout=0.2)
    get_task.assert_no_tasks_called()

    NEXT_TASK_LOCK.release()
    worker.join()
    get_task.assert_all_tasks_called()


def test_worker_pool():
    get_task = GetTaskMock([Mock() for _ in range(5)])
    pool = ResumableWorkerPool(2, get_task)
    pool.join()
    get_task.assert_all_tasks_called()
    for thread in pool.workers:
        assert not thread.is_alive()


def test_worker_pool_concurrency():
    get_task = GetTaskMock(
        [Mock(side_effect=lambda: time.sleep(0.1)) for _ in range(5)]
    )
    start = time.time()
    pool = ResumableWorkerPool(5, get_task)
    pool.join()
    end = time.time()
    assert end - start < 0.2
    get_task.assert_all_tasks_called()
