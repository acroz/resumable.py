from mock import Mock, MagicMock, call

import pytest

from resumable.file import ResumableFile, build_chunks
from test.fixture import (  # noqa: F401
    SAMPLE_CONTENT, TEST_CHUNK_SIZE, SAMPLE_CONTENT_CHUNKS, sample_file
)


@pytest.fixture
def mock_lock(mocker):
    lock = MagicMock()
    mocker.patch('resumable.file.Lock', Mock(return_value=lock))
    return lock


@pytest.fixture
def mock_open(mocker):
    file = Mock(seek=Mock(), read=Mock(), close=Mock())
    open = Mock(return_value=file)
    mocker.patch('resumable.file.open', open)
    return open


def test_build_chunks(sample_file):  # noqa: F811

    read_bytes = Mock()
    file_size = 233
    chunk_size = 100

    chunks = build_chunks(read_bytes, file_size, chunk_size)

    assert len(chunks) == 3

    assert chunks[0].index == 0
    assert chunks[0].size == 100
    chunks[0].read()
    read_bytes.assert_called_once_with(0, 100)
    read_bytes.reset_mock()

    assert chunks[1].index == 1
    assert chunks[1].size == 100
    chunks[1].read()
    read_bytes.assert_called_once_with(100, 100)
    read_bytes.reset_mock()

    assert chunks[2].index == 2
    assert chunks[2].size == 33
    chunks[2].read()
    read_bytes.assert_called_once_with(200, 33)


def test_file(mocker, sample_file):  # noqa: F811
    mock_build_chunks = mocker.patch('resumable.file.build_chunks')

    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)

    assert file.path == sample_file
    assert file.chunk_size == TEST_CHUNK_SIZE
    assert file.size == len(SAMPLE_CONTENT)
    assert file.chunks == mock_build_chunks.return_value

    mock_build_chunks.assert_called_once_with(
        file._read_bytes, len(SAMPLE_CONTENT), TEST_CHUNK_SIZE
    )


def test_close(sample_file, mock_open):  # noqa: F811
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    file.close()
    mock_open.return_value.close.assert_called_once()


def test_mark_chunk_completed(mocker, sample_file):  # noqa: F811

    chunk = Mock()
    mocker.patch('resumable.file.build_chunks', return_value=[chunk])

    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    file.mark_chunk_completed(chunk)

    assert file._chunk_done == {chunk: True}


def test_is_completed(sample_file):  # noqa: F811
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    file._chunk_done = {'one': True, 'two': True, 'three': True}
    assert file.is_completed is True


def test_not_completed(sample_file):  # noqa: F811
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    file._chunk_done = {'one': True, 'two': False, 'three': False}
    assert file.is_completed is False


def test_fraction_completed(sample_file):  # noqa: F811
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    file._chunk_done = {'one': True, 'two': False, 'three': False}
    assert file.fraction_completed == 1. / 3


def test_read_bytes(sample_file):  # noqa: F811
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    assert file._read_bytes(2, 10) == SAMPLE_CONTENT[2:12]


def test_read_bytes_lock(sample_file, mock_lock, mock_open):  # noqa: F811

    # Collect all lock and file related calls together
    manager = Mock(
        lock=mock_lock,
        open=mock_open,
        file=mock_open.return_value
    )

    # Creating a file should cause the file to be opened in rb mode
    file = ResumableFile(sample_file, TEST_CHUNK_SIZE)
    assert manager.mock_calls == [call.open(sample_file, 'rb')]
    manager.reset_mock()

    # Reading bytes from the file should happen in the contect of the lock
    file._read_bytes(2, 10)
    assert manager.mock_calls == [
        call.lock.__enter__(),
        call.file.seek(2),
        call.file.read(10),
        call.lock.__exit__(None, None, None)
    ]
