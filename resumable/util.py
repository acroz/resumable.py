class CallbackDispatcher(object):

    def __init__(self):
        self.targets = []

    def register(self, callback):
        self.targets.append(callback)

    def trigger(self, *args, **kwargs):
        for callback in self.targets:
            callback(*args, **kwargs)


class Config(object):

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return '{0}({1})'.format(
            self.__class__.__name__,
            ', '.join(
                '{0}={1!r}'.format(k, v) for k, v in self.__dict__.items()
            )
        )

    def __eq__(self, other):
        return isinstance(other, Config) and self.__dict__ == other.__dict__
