import pytest
from mock import Mock, call
from six.moves import builtins

import resumable.file
from resumable.file import LazyLoadChunkableFile
from tests.fixture import (  # noqa: F401
    SAMPLE_CONTENT, TEST_CHUNK_SIZE, SAMPLE_CONTENT_CHUNKS, sample_file
)


def test_file(sample_file):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    assert file.path == sample_file
    assert file.chunk_size == TEST_CHUNK_SIZE
    assert file.size == len(SAMPLE_CONTENT)


def test_close(sample_file, mock_open):  # noqa: F811
    file = LazyLoadChunkableFile(sample_file, TEST_CHUNK_SIZE)
    file.close()
    mock_open.return_value.close.assert_called_once()
