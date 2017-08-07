from mock import Mock, MagicMock

from resumable.util import CallbackMixin
from resumable.core import ResumableSignal


def test_register_callback():
    mock_callback = Mock()
    test_signal = ResumableSignal.CHUNK_COMPLETED
    obj = CallbackMixin()
    obj.register_callback(test_signal, mock_callback)
    assert mock_callback in obj.signal_callbacks[test_signal]


def test_proxy_callbacks_to():
    mock_proxy_target = Mock(CallbackMixin)
    obj = CallbackMixin()
    obj.proxy_signals_to(mock_proxy_target)
    assert mock_proxy_target in obj.signal_proxy_targets


def test_send_signal():
    mock_callback = MagicMock()
    mock_proxy_target = MagicMock(CallbackMixin)
    test_signal = ResumableSignal.CHUNK_COMPLETED

    obj = CallbackMixin()
    obj.register_callback(test_signal, mock_callback)
    obj.proxy_signals_to(mock_proxy_target)

    obj.send_signal(test_signal)

    mock_callback.assert_called_once()
    mock_proxy_target.send_signal.assert_called_once_with(test_signal)
