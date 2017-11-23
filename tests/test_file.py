import pytest
from mock import Mock, call
from six.moves import builtins

import resumable.file
from resumable.file import LazyLoadChunkableFile
from tests.fixture import (  # noqa: F401
    SAMPLE_CONTENT, TEST_CHUNK_SIZE, SAMPLE_CONTENT_CHUNKS, sample_file
)


@pytest.fixture
def mock_lock(monkeypatch):
    lock = Mock(__enter__=Mock(), __exit__=Mock())
    monkeypatch.setattr(resumable.file, 'Lock', Mock(return_value=lock))
    return lock


@pytest.fixture
def mock_open(monkeypatch):
    file = Mock(seek=Mock(), read=Mock(), close=Mock())
    open = Mock(return_value=file)
    monkeypatch.setattr(builtins, 'open', open)
    return open


def test_file(sample_file):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.path == sample_file
    assert file.chunk_size == TEST_CHUNK_SIZE
    assert file.size == len(SAMPLE_CONTENT)


def test_close(sample_file, mock_open):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    file.close()
    mock_open.return_value.close.assert_called_once()


def test_read_bytes(sample_file):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.read_bytes(2, 10) == SAMPLE_CONTENT[2:12]


def test_read_bytes_lock(sample_file, mock_lock, mock_open):  # noqa: F811

    # Collect all lock and file related calls together
    manager = Mock(
        lock=mock_lock,
        open=mock_open,
        file=mock_open.return_value
    )

    # Creating a file should cause the file to be opened in rb mode
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert manager.mock_calls == [call.open(sample_file, 'rb')]
    manager.reset_mock()

    # Reading bytes from the file should happen in the contect of the lock
    file.read_bytes(2, 10)
    assert manager.mock_calls == [
        call.lock.__enter__(),
        call.file.seek(2),
        call.file.read(10),
        call.lock.__exit__(None, None, None)
    ]


def test_chunking(sample_file):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert len(list(file.chunks)) == len(SAMPLE_CONTENT_CHUNKS)
    for chunk, expected_data in zip(file.chunks, SAMPLE_CONTENT_CHUNKS):
        assert chunk.data == expected_data
        assert chunk.size == len(expected_data)
