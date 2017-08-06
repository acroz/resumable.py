from resumable.core import Resumable


def test_resumable(mocker):
    worker_pool_mock = mocker.patch('resumable.core.ResumableWorkerPool')
    mock_target = 'https://example.com/upload'
    mock_sim_uploads = 5
    mock_chunk_size = 100
    mock_headers = {'header': 'foo'}

    manager = Resumable(mock_target, mock_sim_uploads, mock_chunk_size,
                        mock_headers)

    assert manager.target == mock_target
    assert manager.chunk_size == mock_chunk_size
    assert manager.headers == mock_headers
    assert manager.files == []

    worker_pool_mock.assert_called_once_with(
        mock_sim_uploads, manager.next_task
    )
