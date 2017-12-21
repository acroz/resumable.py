resumable.py
============

.. image:: https://travis-ci.org/acroz/resumable.py.svg?branch=master
    :target: https://travis-ci.org/acroz/resumable.py
.. image:: https://coveralls.io/repos/github/acroz/resumable.py/badge.svg?branch=master
    :target: https://coveralls.io/github/acroz/resumable.py?branch=master

resumable.py provides chunked uploading of files to a compatible server,
emulating the popular resumable.js_ JavaScript library.

Usage
-----

Construct a ``Resumable`` object with the URL of the upload target server, and
use ``add_file()`` to queue files for upload. It's recommended to use it as a
context manager:

.. code-block:: python

    from resumable import Resumable

    with Resumable('https://example.com/upload') as session:
        session.add_file('my_file.dat')

You can queue mutiple files for upload in a single session, and the ``with``
block will not complete until the upload is finished (or an exception is
raised).

It's also possible to use a ``Resumable`` session without a ``with`` block, and
manually ``join()`` the session:

.. code-block:: python

    session = Resumable('https://example.com/upload')
    session.add_file('my_file.dat')
    do_something_else()
    session.join()

Backend
+++++++

resumable.py handles most of the logic needed for resumable file uploads on the
client side, but the files still need to be reassembled from chunks on the
server side, as in resumable.js_. For details on how to set up a compatible
backend, please see the resumable.js_ documentation or the backend samples
`on GitHub <resumable.js-samples>`_.

Configuration
+++++++++++++

resumable.py supports a subset of the options provided by resumable.js_:

* ``target`` The target URL for the multipart POST request (required)
* ``chunk_size`` The size in bytes of each uploaded chunk of data (default:
  ``1*1024*1024``)
* ``simultaneous_uploads`` Number of simultaneous uploads (default: ``3``)
* ``headers`` Extra headers to include in the multipart POST with data
  (default: ``{}``)
* ``test_chunks`` Make a GET request to the server for each chunks to see if it
  already exists. If implemented on the server-side, this will allow for upload
  resumes even after a browser crash or even a computer restart. (default:
  ``True``)

Some additional low level options are available - these are documented in the
docstring of the ``Resumable`` class.

Callbacks and Progress Reporting
++++++++++++++++++++++++++++++++

resumable.py provides the ability to register arbitrary functions as callbacks
in response to certain events. These are:

On the ``Resumable`` object:

* ``file_added`` Triggered when a file is added, with the file object
* ``file_completed`` Triggered when a file is completed, with the file object
* ``chunk_completed`` Triggered when a chunk is completed, with the file and
  chunk objects

On a ``ResumableFile`` (returned by ``Resumable.add_file()``):

* ``completed`` Triggered when the file is completed, without arguments
* ``chunk_completed`` Triggered when a chunk is completed, with the chunk
  object

Each of these callback dispatchers has a ``register()`` method that you can use
to register callbacks. For example, to print a simple progress message that
updates as chunks are uploaded:

.. code-block:: python

    with Resumable('https://example.com/upload') as session:
        file = session.add_file('my_file.dat')

        def print_progress(chunk):
            template = '\rPercent complete: {:.1%}'
            print(template.format(file.fraction_completed), end='')

        file.chunk_completed.register(print_progress)

    print()  # new line

Contribute
----------

resumable.py's design is informed by resumable.js_, however only a core subset
of features have yet been implemented. Patches implementing resumable.js
features are welcome, and contributors should attempt to retain consistency
with the resumable.js interface, mapping JavaScript style and idioms to Python
equivalents as appropriate (for example, the ``simultaneousUploads``
configuration parameter becomes ``simultaneous_uploads`` in Python).

.. _resumable.js: http://resumablejs.com
.. _resumable.js-samples: https://github.com/23/resumable.js/tree/master/samples
