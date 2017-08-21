from collections import defaultdict


class CallbackMixin(object):

    def __init__(self, *args, **kwargs):
        super(CallbackMixin, self).__init__(*args, **kwargs)
        self.signal_callbacks = defaultdict(list)
        self.signal_proxy_targets = []

    def register_callback(self, signal, callback):
        self.signal_callbacks[signal].append(callback)

    def proxy_signals_to(self, target):
        self.signal_proxy_targets.append(target)

    def send_signal(self, signal):
        for callback in self.signal_callbacks[signal]:
            callback()
        for target in self.signal_proxy_targets:
            target.send_signal(signal)


class Config(object):

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(
                '{}={}'.format(k, repr(v)) for k, v in self.__dict__.items()
            )
        )

    def __eq__(self, other):
        return isinstance(other, Config) and self.__dict__ == other.__dict__
