from setuptools import setup


setup(
    name='resumable',
    version='0.1.0',
    description='Chunked upload to a server supporting resumable.js',
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
