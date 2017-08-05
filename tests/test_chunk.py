from mock import Mock, MagicMock, patch
import requests
import pytest

from resumable.core import ResumableChunk, ResumableChunkState, ResumableSignal


def test_query():
    """Query merges its own with that of its source file."""
    mock_file = Mock(query={'dummy': 'query'})
    mock_chunk = Mock(index=3, size=100)
    chunk = ResumableChunk(mock_file, mock_chunk)
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
    mock_target = 'https://example.com/upload'
    mock_query = {'query': 'foo'}
    mock_headers = {'header': 'bar'}
    mock_send_signal = MagicMock()

    requests_get_mock = MagicMock(
        return_value=Mock(requests.Response, status_code=get_response_code)
    )

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(Mock(), Mock())
        with patch('requests.get', requests_get_mock):
            chunk.test(mock_target, mock_headers)

    requests_get_mock.assert_called_once_with(
        mock_target, headers=mock_headers, data=mock_query
    )
    assert chunk.state == expected_state
    if expected_state == ResumableChunkState.DONE:
        mock_send_signal.assert_called_once_with(
            ResumableSignal.CHUNK_COMPLETED
        )


def test_send():
    mock_target = 'https://example.com/upload'
    mock_query = {'query': 'foo'}
    mock_headers = {'header': 'bar'}
    mock_data = b'data'
    mock_send_signal = MagicMock()

    requests_post_mock = MagicMock(return_value=Mock(requests.Response))

    with patch.multiple(ResumableChunk, query=mock_query,
                        send_signal=mock_send_signal):
        chunk = ResumableChunk(Mock(), Mock(data=mock_data))
        with patch('requests.post', requests_post_mock):
            chunk.send(mock_target, mock_headers)

    requests_post_mock.assert_called_once_with(
        mock_target, headers=mock_headers, data=mock_query,
        files={'file': mock_data}
    )
    assert chunk.state == ResumableChunkState.DONE
    mock_send_signal.assert_called_once_with(
        ResumableSignal.CHUNK_COMPLETED
    )
