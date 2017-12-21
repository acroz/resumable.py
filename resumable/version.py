import platform

__version__ = '0.1.1'


def user_agent():
    """Return user agent string."""
    return 'resumable.py/{} (Python {})'.format(
        __version__,
        platform.python_version()
    )
