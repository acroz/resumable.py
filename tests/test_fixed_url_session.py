from mock import MagicMock
import requests

from resumable.util import FixedUrlSession


MOCK_URL = 'https://example.com/endpoint'


def test_get():
    mock_session = MagicMock(requests.Session)
    wrapped = FixedUrlSession(mock_session, MOCK_URL)
    assert wrapped.get(foo='bar') == mock_session.get.return_value
    mock_session.get.assert_called_once_with(MOCK_URL, foo='bar')


def test_post():
    mock_session = MagicMock(requests.Session)
    wrapped = FixedUrlSession(mock_session, MOCK_URL)
    assert wrapped.post(foo='bar') == mock_session.post.return_value
    mock_session.post.assert_called_once_with(MOCK_URL, foo='bar')
