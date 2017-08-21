import pytest

from resumable.util import Config


def test_config():
    config = Config(foo='bar')
    assert config.foo == 'bar'


def test_setattr():
    config = Config()
    config.foo = 'bar'
    assert config.foo == 'bar'


def test_str():
    assert str(Config(foo='one', bar='two')) in [
        "Config(foo='one', bar='two')",
        "Config(bar='two', foo='one')"
    ]


def test_eq():
    assert Config(foo='bar') == Config(foo='bar')


@pytest.mark.parametrize('other', [
    Config(),
    Config(foo='other'),
    Config(foo='bar', other='other')
])
def test_neq(other):
    assert Config(foo='bar') != other
