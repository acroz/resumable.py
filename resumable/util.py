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


class FixedUrlSession(object):
    """A simple wrapper for requests.Session that fixes the URL."""

    def __init__(self, session, url):
        self.session = session
        self.url = url

    def get(self, *args, **kwargs):
        return self.session.get(self.url, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(self.url, *args, **kwargs)
