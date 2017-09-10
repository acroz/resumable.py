import socket
import time
import multiprocessing
from collections import namedtuple

import requests
import flask
import pytest


Request = namedtuple('Request', ['method', 'data'])


def _available_port():
    """Find a free port to run the test server on."""
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    _, port = tcp.getsockname()
    tcp.close()
    return port


def _run_server(queue, port):

    app = flask.Flask('testserver')

    @app.route('/upload', methods=['GET', 'POST'])
    def upload():
        form_first_fields = {(k, v) for k, v in flask.request.form.items()}
        queue.put(Request(flask.request.method, form_first_fields))
        if flask.request.method == 'GET':
            return '', 404
        else:
            return '', 200

    app.run(port=port)


class Server(object):

    def __init__(self):
        self.process = None
        self.port = None
        self._received_queue = multiprocessing.Queue()
        self._received = []

    @property
    def url(self):
        if self.port is None:
            raise RuntimeError('server not started yet')
        return 'http://localhost:{}'.format(self.port)

    @property
    def endpoint(self):
        return '{}/upload'.format(self.url)

    @property
    def received(self):
        while not self._received_queue.empty():
            self._received.append(self._received_queue.get())
        return self._received

    def start(self):
        self.port = _available_port()
        self.process = multiprocessing.Process(
            target=_run_server,
            args=(self._received_queue, self.port)
        )
        self.process.start()
        self._wait_until_up()

    def _wait_until_up(self, timeout=5.0):
        start = time.time()
        while time.time() - start < timeout:
            try:
                requests.get(self.url)
            except requests.exceptions.ConnectionError:
                time.sleep(0.1)
            else:
                break
        else:
            raise RuntimeError('server startup check timed out')

    def stop(self):
        if self.process is not None:
            self.process.terminate()


@pytest.fixture
def server():
    test_server = Server()
    try:
        test_server.start()
        yield test_server
    finally:
        test_server.stop()
