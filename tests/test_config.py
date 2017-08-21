import pytest

from resumable.util import Config


def test_config():
    config = Config(foo='bar')
    assert config.foo == 'bar'


def test_config_setattr():
    config = Config()
    config.foo = 'bar'
    assert config.foo == 'bar'


def test_config_eq():
    assert Config(foo='bar') == Config(foo='bar')


@pytest.mark.parametrize('other', [
    Config(),
    Config(foo='other'),
    Config(foo='bar', other='other')
])
def test_config_neq(other):
    assert Config(foo='bar') != other
