import os
import mimetypes


class ResumableError(Exception):
    pass


def resolve_chunk(session, config, file, chunk):

    exists_on_server = False
    if config.test_chunks:
        exists_on_server = _test_chunk(session, config, file, chunk)

    if not exists_on_server:
        tries = 0
        while not _send_chunk(session, config, file, chunk):
            tries += 1
            if tries >= config.max_chunk_retries:
                raise ResumableError('max retries exceeded')

    file.mark_chunk_completed(chunk)


def _test_chunk(session, config, file, chunk):
    response = session.get(
        config.target,
        data=_build_query(file, chunk)
    )
    return response.status_code == 200


def _send_chunk(session, config, file, chunk):
    response = session.post(
        config.target,
        data=_build_query(file, chunk),
        files={'file': chunk.read()}
    )
    if response.status_code in config.permanent_errors:
        # TODO: better exception
        raise ResumableError('permanent error')
    return response.status_code in [200, 201]


def _build_query(file, chunk):
    return {
        'resumableChunkSize': file.chunk_size,
        'resumableTotalSize': file.size,
        'resumableType': _file_type(file.path),
        'resumableIdentifier': str(file.unique_identifier),
        'resumableFilename': os.path.basename(file.path),
        'resumableRelativePath': file.path,
        'resumableTotalChunks': len(file.chunks),
        'resumableChunkNumber': chunk.index + 1,
        'resumableCurrentChunkSize': chunk.size
    }


def _file_type(path):
    """Mimic the type parameter of a JS File object.

    Resumable.js uses the File object's type attribute to guess mime type,
    which is guessed from file extention accoring to
    https://developer.mozilla.org/en-US/docs/Web/API/File/type.
    """
    type_, _ = mimetypes.guess_type(path)
    # When no type can be inferred, File.type returns an empty string
    return '' if type_ is None else type_
