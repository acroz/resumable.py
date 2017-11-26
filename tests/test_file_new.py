from mock import Mock
from resumable.file import FileChunk, build_chunks
from tests.fixture import (  # noqa: F401
    SAMPLE_CONTENT, TEST_CHUNK_SIZE, SAMPLE_CONTENT_CHUNKS, sample_file
)


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
