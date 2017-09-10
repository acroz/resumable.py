import pytest


SAMPLE_CONTENT = b'sample content afsdfas'
TEST_CHUNK_SIZE = 10


def _chunk_content(content, size):
    chunks = []
    start = 0
    while start < len(content):
        chunks.append(content[start:start+size])
        start += size
    return chunks


SAMPLE_CONTENT_CHUNKS = _chunk_content(SAMPLE_CONTENT, TEST_CHUNK_SIZE)


@pytest.fixture
def sample_file(tmpdir):
    path = tmpdir.join('sample-file.txt')
    path.write(SAMPLE_CONTENT)
    return path
