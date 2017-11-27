from mock import Mock
import pytest

from resumable.util import Config
from resumable.file import FileChunk
from resumable.chunk import ResumableError, resolve_chunk


TEST_TARGET = 'http://example.com/upload'
TEST_PATH = '/path/to/file.txt'
TEST_CHUNK_SIZE = 100
TEST_FILE_SIZE = 123


def mock_session(test_status=404, send_status=200):
    test_response = Mock(status_code=test_status)
    send_response = Mock(status_code=send_status)
    session = Mock(
        get=Mock(return_value=test_response),
        post=Mock(return_value=send_response)
    )
    return session


def mock_file():
    return Mock(
        path=TEST_PATH,
        size=TEST_FILE_SIZE,
        chunk_size=TEST_CHUNK_SIZE,
        unique_identifier='unique identifier',
        chunks=['foo', 'bar']
    )


def expected_form_data():
    return {
        'resumableChunkSize': TEST_CHUNK_SIZE,
        'resumableTotalSize': TEST_FILE_SIZE,
        'resumableType': 'text/plain',
        'resumableIdentifier': 'unique identifier',
        'resumableFilename': TEST_PATH.split('/')[-1],
        'resumableRelativePath': TEST_PATH,
        'resumableTotalChunks': 2,
        'resumableChunkNumber': 1,
        'resumableCurrentChunkSize': 100
    }


@pytest.mark.parametrize('test_status', [404, 500])
def test_resolve_chunk(test_status):

    session = mock_session()
    config = Config(
        target=TEST_TARGET,
        test_chunks=True,
        permanent_errors=[500]
    )
    file = mock_file()
    chunk = FileChunk(index=0, size=100, read=Mock())

    resolve_chunk(session, config, file, chunk)

    session.get.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data()
    )
    session.post.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data(),
        files={'file': chunk.read.return_value}
    )
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_exists():

    session = mock_session(test_status=200)
    config = Config(
        target=TEST_TARGET,
        test_chunks=True,
        permanent_errors=[500]
    )
    file = mock_file()
    chunk = FileChunk(index=0, size=100, read=Mock())

    resolve_chunk(session, config, file, chunk)

    session.get.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data()
    )
    session.post.assert_not_called()
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_no_test():

    session = mock_session()
    config = Config(
        target=TEST_TARGET,
        test_chunks=False,
        permanent_errors=[500]
    )
    file = mock_file()
    chunk = FileChunk(index=0, size=100, read=Mock())

    resolve_chunk(session, config, file, chunk)

    session.get.assert_not_called()
    session.post.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data(),
        files={'file': chunk.read.return_value}
    )
    file.mark_chunk_completed.assert_called_once_with(chunk)


def test_resolve_chunk_send_permanent_error():

    session = mock_session(send_status=500)
    config = Config(
        target=TEST_TARGET,
        test_chunks=True,
        permanent_errors=[500]
    )
    file = mock_file()
    chunk = FileChunk(index=0, size=100, read=Mock())

    with pytest.raises(ResumableError):
        resolve_chunk(session, config, file, chunk)

    session.get.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data()
    )
    session.post.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data(),
        files={'file': chunk.read.return_value}
    )
    file.mark_chunk_completed.assert_not_called()


def test_resolve_chunk_send_exceed_max_retries():

    session = mock_session(send_status=418)
    config = Config(
        target=TEST_TARGET,
        test_chunks=True,
        permanent_errors=[500],
        max_chunk_retries=10
    )
    file = mock_file()
    chunk = FileChunk(index=0, size=100, read=Mock())

    with pytest.raises(ResumableError):
        resolve_chunk(session, config, file, chunk)

    session.get.assert_called_once_with(
        TEST_TARGET,
        data=expected_form_data()
    )
    assert session.post.call_count == 10
    session.post.assert_called_with(
        TEST_TARGET,
        data=expected_form_data(),
        files={'file': chunk.read.return_value}
    )
    file.mark_chunk_completed.assert_not_called()
