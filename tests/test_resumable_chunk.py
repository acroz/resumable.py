from mock import Mock, MagicMock, patch
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


@pytest.mark.parametrize('get_response_code, expected_state', [
    (404, ResumableChunkState.QUEUED),
    (200, ResumableChunkState.DONE)
])
def test_test(get_response_code, expected_state):
    mock_session = MagicMock(requests.Session)
    mock_session.get.return_value = Mock(requests.Response,
                                         status_code=get_response_code)
    mock_config = Config(target='mock-target')
    mock_query = {'query': 'foo'}
    mock_send_signal = MagicMock()

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(mock_session, mock_config, Mock(), Mock())
        chunk.test()

    mock_session.get.assert_called_once_with(
        mock_config.target,
        data=mock_query
    )
    assert chunk.state == expected_state
    if expected_state == ResumableChunkState.DONE:
        mock_send_signal.assert_called_once_with(
            ResumableSignal.CHUNK_COMPLETED
        )


def test_send():
    mock_session = MagicMock(requests.Session)
    mock_session.post.return_value = Mock(requests.Response, status_code=200)
    mock_config = Config(target='mock-target')
    mock_query = {'query': 'foo'}
    mock_data = b'data'
    mock_send_signal = MagicMock()

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
    assert chunk.state == ResumableChunkState.DONE
    mock_send_signal.assert_called_once_with(ResumableSignal.CHUNK_COMPLETED)


@pytest.mark.parametrize('state, should_send', [
    (ResumableChunkState.QUEUED, True),
    (ResumableChunkState.POPPED, True),
    (ResumableChunkState.DONE, False)
])
def test_send_if_not_done(state, should_send):
    mock_send = MagicMock()

    with patch.multiple(ResumableChunk, send=mock_send):
        chunk = ResumableChunk(Mock(), Mock(), Mock(), Mock())
        chunk.state = state
        chunk.send_if_not_done()

    if should_send:
        mock_send.assert_called_once()
    else:
        mock_send.assert_not_called()


def test_create_task():
    mock_test = MagicMock()
    mock_send_if_not_done = MagicMock()

    with patch.multiple(ResumableChunk, test=mock_test,
                        send_if_not_done=mock_send_if_not_done):
        chunk = ResumableChunk(Mock(), Mock(), Mock(), Mock())
        task = chunk.create_task()
        assert chunk.state == ResumableChunkState.POPPED
        task()

    mock_test.assert_called_once()
    mock_send_if_not_done.assert_called_once()
