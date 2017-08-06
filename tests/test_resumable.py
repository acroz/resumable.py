import pytest
from mock import MagicMock

from resumable.core import Resumable, ResumableFile, ResumableSignal
from resumable.file import LazyLoadChunkableFile


MOCK_TARGET = 'https://example.com/upload'


@pytest.fixture
def worker_pool_mock(mocker):
    return mocker.patch('resumable.core.ResumableWorkerPool')


def test_resumable(worker_pool_mock):
    mock_sim_uploads = 5
    mock_chunk_size = 100
    mock_headers = {'header': 'foo'}

    manager = Resumable(MOCK_TARGET, mock_sim_uploads, mock_chunk_size,
                        mock_headers)

    assert manager.target == MOCK_TARGET
    assert manager.chunk_size == mock_chunk_size
    assert manager.headers == mock_headers
    assert manager.files == []

    worker_pool_mock.assert_called_once_with(
        mock_sim_uploads, manager.next_task
    )


def test_add_file(mocker, worker_pool_mock):
    lazy_load_file_mock = mocker.patch('resumable.core.LazyLoadChunkableFile')
    file_mock = mocker.patch('resumable.core.ResumableFile')

    mock_path = '/mock/path'

    manager = Resumable(MOCK_TARGET)
    manager.send_signal = MagicMock()

    manager.add_file(mock_path)

    lazy_load_file_mock.assert_called_once_with(mock_path, manager.chunk_size)
    file_mock.assert_called_once_with(lazy_load_file_mock.return_value)
    assert manager.files == [file_mock.return_value]
    manager.send_signal.assert_called_once_with(ResumableSignal.FILE_ADDED)
    file_mock.return_value.proxy_signals_to.assert_called_once_with(manager)


def test_wait_until_complete(worker_pool_mock):
    manager = Resumable(MOCK_TARGET)
    manager.wait_until_complete()
    worker_pool_mock.return_value.join.assert_called_once()
