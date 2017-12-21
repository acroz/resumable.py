import os
from setuptools import setup


def source_root():
    """Get the root of the source."""
    return os.path.abspath(os.path.dirname(__file__))


def read_version():
    """Read the version from the resumable.version module."""
    filename = os.path.join(source_root(), 'resumable/version.py')
    with open(filename) as fp:
        namespace = {}
        exec(fp.read(), namespace)  # pylint: disable=exec-used
        return namespace['__version__']


def read_long_description():
    """Read the README file."""
    filename = os.path.join(source_root(), 'README.rst')
    with open(filename) as fp:
        return fp.read()


setup(
    name='resumable',
    version=read_version(),
    description='Python client for upload to a server supporting resumable.js',
    long_description=read_long_description(),
    url='https://acroz.github.com/acroz/resumable.py',
    author='Andrew Crozier',
    author_email='wacrozier@gmail.com',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    packages=['resumable'],
    setup_requires=[
        'pytest-runner',
        'wheel'
    ],
    tests_require=[
        'pytest',
        'pytest-cov',
        'mock',
        'pytest-mock',
        'six',
        'flask'
    ],
    install_requires=[
        'requests',
        'futures; python_version == "2.7"'
    ]
)
