from resumable import Resumable

from test.fixture import (  # noqa: F401
    SAMPLE_CONTENT, TEST_CHUNK_SIZE, SAMPLE_CONTENT_CHUNKS, sample_file,
    server, Request
)


def expected_body(identifier, testfile, index, content):
    body = {
        'resumableChunkNumber': index + 1,
        'resumableCurrentChunkSize': len(content),
        'resumableChunkSize': TEST_CHUNK_SIZE,
        'resumableTotalSize': len(SAMPLE_CONTENT),
        'resumableType': 'text/plain',
        'resumableIdentifier': identifier,
        'resumableFilename': testfile.basename,
        'resumableRelativePath': testfile,
        'resumableTotalChunks': len(SAMPLE_CONTENT_CHUNKS)
    }
    return set([(k, str(v)) for k, v in body.items()])


def expected_requests(resumable_file, testfile):
    all_requests = []
    for i, chunk_data in enumerate(SAMPLE_CONTENT_CHUNKS):
        body = expected_body(resumable_file.unique_identifier, testfile, i,
                             chunk_data)
        all_requests.append(Request('GET', body))
        all_requests.append(Request('POST', body))
    return all_requests


def test_resumable(server, sample_file):  # noqa: F811

    with Resumable(
        target=server.endpoint,
        chunk_size=TEST_CHUNK_SIZE,
        simultaneous_uploads=1
    ) as r:
        resumable_file = r.add_file(sample_file)

    expected = expected_requests(resumable_file, sample_file)
    assert sorted(server.received) == sorted(expected)
