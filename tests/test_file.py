import pytest

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


def test_file(sample_file):
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.path == sample_file
    assert file.chunk_size == TEST_CHUNK_SIZE
    assert file.size == len(SAMPLE_CONTENT)


def test_chunking(sample_file):
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert len(list(file.chunks)) == len(list(expected_chunk_data()))
    for chunk, expected_data in zip(file.chunks, expected_chunk_data()):
        assert chunk.data == expected_data
        assert chunk.size == len(expected_data)
