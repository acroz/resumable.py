from mock import Mock, call
import pytest

from resumable.util import Config
from resumable.file import FileChunk
from resumable.chunk import ResumableError, resolve_chunk


TEST_TARGET = 'http://example.com/upload'
TEST_PATH = '/path/to/file.txt'
TEST_CHUNK_SIZE = 100
TEST_FILE_SIZE = 123
MOCK_CHUNK_DATA = 'foo ' * 25


def mock_session(test_status=404, send_status=200):
    test_response = Mock(status_code=test_status)
    send_response = Mock(status_code=send_status)
    session = Mock(
        get=Mock(return_value=test_response),
        post=Mock(return_value=send_response)
    )
    return session


def mock_file(path=TEST_PATH):
    return Mock(
        path=path,
        size=TEST_FILE_SIZE,
        chunk_size=TEST_CHUNK_SIZE,
        unique_identifier='unique identifier',
        chunks=['foo', 'bar']
    )


def mock_chunk():
    return FileChunk(
        index=0, size=100, read=Mock(return_value=MOCK_CHUNK_DATA)
    )


def expected_form_data(path=TEST_PATH, file_type='text/plain'):
    return {
        'resumableChunkSize': TEST_CHUNK_SIZE,
        'resumableTotalSize': TEST_FILE_SIZE,
        'resumableType': file_type,
        'resumableIdentifier': 'unique identifier',
        'resumableFilename': path.split('/')[-1],
        'resumableRelativePath': path,
        'resumableTotalChunks': 2,
        'resumableChunkNumber': 1,
        'resumableCurrentChunkSize': 100
    }


def assert_get(session, **kwargs):
    session.get.assert_called_once_with(
        TEST_TARGET, data=expected_form_data(**kwargs)
    )


def assert_post(session, times=1, **kwargs):
    single_call = call(
        TEST_TARGET, data=expected_form_data(**kwargs),
        files={'file': MOCK_CHUNK_DATA}
    )
    session.post.assert_has_calls([single_call] * times)


@pytest.mark.parametrize('path, file_type, test_status', [
    (TEST_PATH, 'text/plain', 404),
    (TEST_PATH, 'text/plain', 500),
    ('/path/to/file.json', 'application/json', 404),
    ('/path/no-extension', '', 404)
])
def test_resolve_chunk(path, file_type, test_status):

    session = mock_session()
    config = Config(
        target=TEST_TARGET, test_chunks=True, permanent_errors=[500]
    )
    file = mock_file(path)
    chunk = mock_chunk()

    resolve_chunk(session, config, file, chunk)

    assert_get(session, path=path, file_type=file_type)
    assert_post(session, path=path, file_type=file_type)
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_exists():

    session = mock_session(test_status=200)
    config = Config(
        target=TEST_TARGET, test_chunks=True, permanent_errors=[500]
    )
    file = mock_file()
    chunk = mock_chunk()

    resolve_chunk(session, config, file, chunk)

    assert_get(session)
    session.post.assert_not_called()
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_no_test():

    session = mock_session()
    config = Config(
        target=TEST_TARGET, test_chunks=False, permanent_errors=[500]
    )
    file = mock_file()
    chunk = mock_chunk()

    resolve_chunk(session, config, file, chunk)

    session.get.assert_not_called()
    assert_post(session)
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_send_permanent_error():

    session = mock_session(send_status=500)
    config = Config(
        target=TEST_TARGET, test_chunks=True, permanent_errors=[500]
    )
    file = mock_file()
    chunk = mock_chunk()

    with pytest.raises(ResumableError):
        resolve_chunk(session, config, file, chunk)

    assert_get(session)
    assert_post(session)
    file.mark_chunk_completed.assert_not_called()


def test_resolve_chunk_send_exceed_max_retries():

    session = mock_session(send_status=418)
    config = Config(
        target=TEST_TARGET, test_chunks=True, permanent_errors=[500],
        max_chunk_retries=10
    )
    file = mock_file()
    chunk = mock_chunk()

    with pytest.raises(ResumableError):
        resolve_chunk(session, config, file, chunk)

    assert_get(session)
    assert_post(session, times=10)
    file.mark_chunk_completed.assert_not_called()
