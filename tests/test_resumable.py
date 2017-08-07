import pytest
from mock import Mock, MagicMock

from resumable.core import Resumable, ResumableSignal, ResumableChunkState


MOCK_TARGET = 'https://example.com/upload'


@pytest.fixture
def session_mock(mocker):
    return mocker.patch('requests.Session')


@pytest.fixture
def worker_pool_mock(mocker):
    return mocker.patch('resumable.core.ResumableWorkerPool')


def test_resumable(session_mock, worker_pool_mock):
    mock_sim_uploads = 5
    mock_chunk_size = 100
    mock_headers = {'header': 'foo'}

    manager = Resumable(MOCK_TARGET, mock_sim_uploads, mock_chunk_size,
                        mock_headers)

    assert manager.target == MOCK_TARGET
    assert manager.chunk_size == mock_chunk_size

    assert manager.session == session_mock.return_value
    manager.session.headers.update.assert_called_once_with(mock_headers)

    assert manager.files == []

    assert manager.worker_pool == worker_pool_mock.return_value
    worker_pool_mock.assert_called_once_with(
        mock_sim_uploads, manager.next_task
    )


def test_add_file(mocker, session_mock, worker_pool_mock):
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


def test_wait_until_complete(session_mock, worker_pool_mock):
    manager = Resumable(MOCK_TARGET)
    manager.wait_until_complete()
    worker_pool_mock.return_value.join.assert_called_once()


def test_close(session_mock, worker_pool_mock):
    manager = Resumable(MOCK_TARGET)
    manager.files = [MagicMock(), MagicMock(), MagicMock()]
    manager.close()

    # TODO: should also ensure worker pool is closed
    for mock_file in manager.files:
        mock_file.close.assert_called_once()


def test_context_manager(session_mock, worker_pool_mock):
    manager = Resumable(MOCK_TARGET)
    manager.wait_until_complete = MagicMock()
    manager.close = MagicMock()

    with manager as entered_manager:
        assert manager == entered_manager

    manager.wait_until_complete.assert_called_once()
    manager.close.assert_called_once()


def test_chunks(session_mock, worker_pool_mock):
    manager = Resumable(MOCK_TARGET)
    manager.files = [
        Mock(chunks=range(4)),
        Mock(chunks=range(4, 6)),
        Mock(chunks=range(6, 10))
    ]
    assert list(manager.chunks) == list(range(10))


def test_next_task(mocker, session_mock, worker_pool_mock):
    fixed_url_session_mock = mocker.patch('resumable.core.FixedUrlSession')
    mock_chunks = [
        Mock(state=ResumableChunkState.DONE),
        Mock(state=ResumableChunkState.POPPED),
        Mock(state=ResumableChunkState.UPLOADING),
        Mock(state=ResumableChunkState.QUEUED),
        Mock(state=ResumableChunkState.QUEUED)
    ]
    mocker.patch.object(Resumable, 'chunks', mock_chunks)
    manager = Resumable(MOCK_TARGET)
    assert manager.next_task() == mock_chunks[3].create_task.return_value
    mock_chunks[3].create_task.assert_called_once_with(
        fixed_url_session_mock.return_value
    )
    fixed_url_session_mock.assert_called_once_with(
        session_mock.return_value, MOCK_TARGET
    )
