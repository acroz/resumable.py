import os.path
from setuptools import find_packages, setup


setup(
    name='resumable',
    version='0.0.0-dev0',
    description='Chunked upload to a server supporting resumable.js',
    url='https://acroz.github.io',
    author='Andrew Crozier',
    author_email='wacrozier@gmail.com',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages()
)
