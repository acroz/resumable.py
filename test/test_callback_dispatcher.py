from mock import Mock

from resumable.util import CallbackDispatcher


def test_callback_dispatcher():

    callbacks = [Mock(), Mock()]

    dispatcher = CallbackDispatcher()
    for callback in callbacks:
        dispatcher.register(callback)

    dispatcher.trigger('foo', 'bar', key='value')

    for callback in callbacks:
        callback.assert_called_once_with('foo', 'bar', key='value')
