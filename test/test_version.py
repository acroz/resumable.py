from resumable.version import user_agent


def test_user_agent(mocker):
    mocker.patch('resumable.version.__version__', 'resumable-version')
    mocker.patch('platform.python_version', return_value='python-version')

    expected = 'resumable.py/resumable-version (Python python-version)'
    assert user_agent() == expected
