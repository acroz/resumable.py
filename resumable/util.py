class FixedUrlSession(object):
    """A simple wrapper for requests.Session that fixes the URL."""

    def __init__(self, session, url):
        self.session = session
        self.url = url

    def get(self, *args, **kwargs):
        return self.session.get(self.url, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(self.url, *args, **kwargs)
