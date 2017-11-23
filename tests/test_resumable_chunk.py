from mock import Mock, patch, call
import requests
import pytest

from resumable.core import ResumableChunk, ResumableChunkState, ResumableSignal
from resumable.util import Config


def test_query():
    """Query merges its own with that of its source file."""
    mock_file = Mock(query={'dummy': 'query'})
    mock_chunk = Mock(index=3, size=100)
    chunk = ResumableChunk(Mock(), Mock(), mock_file, mock_chunk)
    assert chunk.query == {
        'dummy': 'query',
        'resumableChunkNumber': 4,
        'resumableCurrentChunkSize': 100
    }


@pytest.mark.parametrize('status_code, status, signal', [
    (404, ResumableChunkState.PENDING, None),
    (200, ResumableChunkState.SUCCESS, ResumableSignal.CHUNK_COMPLETED)
])
def test_test(status_code, status, signal):
    mock_session = Mock(requests.Session)
    mock_session.get.return_value = Mock(requests.Response,
                                         status_code=status_code)
    mock_config = Config(target='mock-target')
    mock_query = {'query': 'foo'}
    mock_send_signal = Mock()

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(mock_session, mock_config, Mock(), Mock())
        chunk.test()

    mock_session.get.assert_called_once_with(
        mock_config.target,
        data=mock_query
    )
    assert chunk.status == status
    if signal:
        mock_send_signal.assert_called_once_with(signal)


@pytest.mark.parametrize('status_code, status, signal', [
    (200, ResumableChunkState.SUCCESS, ResumableSignal.CHUNK_COMPLETED),
    (400, ResumableChunkState.ERROR, ResumableSignal.CHUNK_FAILED),
    (418, ResumableChunkState.PENDING, ResumableSignal.CHUNK_RETRY)
])
def test_send(status_code, status, signal):
    mock_session = Mock(requests.Session)
    mock_session.post.return_value = Mock(requests.Response,
                                          status_code=status_code)
    mock_config = Config(target='mock-target',
                         max_chunk_retries=100,
                         permanent_errors=[400])
    mock_query = {'query': 'foo'}
    mock_data = b'data'
    mock_send_signal = Mock()

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(mock_session, mock_config, Mock(),
                               Mock(data=mock_data))
        chunk.send()

    mock_session.post.assert_called_once_with(
        mock_config.target,
        data=mock_query,
        files={'file': mock_data}
    )
    assert chunk.status == status
    mock_send_signal.assert_called_once_with(signal)


def test_retry():
    mock_session = Mock(requests.Session)
    mock_session.post.return_value = Mock(requests.Response, status_code=418)
    mock_config = Config(target='mock-target',
                         max_chunk_retries=2,
                         permanent_errors=[400])
    mock_query = {'query': 'foo'}
    mock_data = b'data'
    mock_send_signal = Mock()

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(mock_session, mock_config, Mock(),
                               Mock(data=mock_data))

        chunk.send()
        assert chunk.status == ResumableChunkState.PENDING

        chunk.send()
        assert chunk.status == ResumableChunkState.PENDING

        chunk.send()
        assert chunk.status == ResumableChunkState.ERROR

    mock_send_signal.assert_has_calls([
        call(ResumableSignal.CHUNK_RETRY),
        call(ResumableSignal.CHUNK_RETRY),
        call(ResumableSignal.CHUNK_FAILED)
    ])


@pytest.mark.parametrize('test_success', [True, False])
def test_resolve_with_test(test_success):
    mock_config = Config(test_chunks=True)

    chunk = ResumableChunk(Mock(), mock_config, Mock(), Mock())

    def set_status():
        if test_success:
            chunk.status = ResumableChunkState.SUCCESS
    chunk.test = Mock(side_effect=set_status)
    chunk.send = Mock()

    chunk.resolve()

    chunk.test.assert_called_once()
    if test_success:
        chunk.send.assert_not_called()
    else:
        chunk.send.assert_called_once()


def test_resolve_no_test():
    mock_config = Config(test_chunks=False)

    chunk = ResumableChunk(Mock(), mock_config, Mock(), Mock())
    chunk.test = Mock()
    chunk.send = Mock()

    chunk.resolve()

    chunk.test.assert_not_called()
    chunk.send.assert_called_once()


def test_create_task():
    chunk = ResumableChunk(Mock(), Mock(), Mock(), Mock())
    chunk.resolve = Mock()

    task = chunk.create_task()

    assert chunk.status == ResumableChunkState.POPPED
    assert task == chunk.resolve
