import pytest
from mock import Mock, MagicMock, call
from six.moves import builtins

import resumable.file
from resumable.file import LazyLoadChunkableFile


SAMPLE_CONTENT = b"sample content afsdfas"
TEST_CHUNK_SIZE = 10


def expected_chunk_data():
    start = 0
    while start < len(SAMPLE_CONTENT):
        yield SAMPLE_CONTENT[start:start+TEST_CHUNK_SIZE]
        start += TEST_CHUNK_SIZE


@pytest.fixture
def sample_file(tmpdir):
    path = tmpdir.join('sample-file.txt')
    path.write(SAMPLE_CONTENT)
    return path


@pytest.fixture
def mock_lock(monkeypatch):
    lock = Mock(__enter__=MagicMock(), __exit__=MagicMock())
    monkeypatch.setattr(resumable.file, 'Lock', Mock(return_value=lock))
    return lock


@pytest.fixture
def mock_open(monkeypatch):
    file = Mock(seek=MagicMock(), read=MagicMock())
    open = MagicMock(return_value=file)
    monkeypatch.setattr(builtins, 'open', open)
    return open


def test_file(sample_file):
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.path == sample_file
    assert file.chunk_size == TEST_CHUNK_SIZE
    assert file.size == len(SAMPLE_CONTENT)


def test_read_bytes(sample_file):
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.read_bytes(2, 10) == SAMPLE_CONTENT[2:12]


def test_read_bytes_lock(sample_file, mock_lock, mock_open):

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


def test_chunking(sample_file):
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert len(list(file.chunks)) == len(list(expected_chunk_data()))
    for chunk, expected_data in zip(file.chunks, expected_chunk_data()):
        assert chunk.data == expected_data
        assert chunk.size == len(expected_data)
