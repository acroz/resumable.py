# resumable.py

[![Build](https://travis-ci.org/acroz/resumable.py.svg?branch=master)](https://travis-ci.org/acroz/resumable.py)
[![Coverage](https://coveralls.io/repos/github/acroz/resumable.py/badge.svg?branch=master)](https://coveralls.io/github/acroz/resumable.py?branch=master)

resumable.py provides chunked uploading of files to a compatible server,
emulating the popular [resumable.js] JavaScript library.

## Usage

Construct a `Resumable` object with the URL of the upload target server, and
use `add_file()` to queue files for upload. It's recommended to use it as a
context manager:

```python
from resumable import Resumable

with Resumable('https://example.com/upload') as session:
    session.add_file('my_file.dat')
```

You can queue mutiple files for upload in a single session, and the `with`
block will not complete until the upload is finished (or an exception is
raised).

It's also possible to use a `Resumable` session without a `with` block, and
manually `join()` the session:

```python
session = Resumable('https://example.com/upload')
session.add_file('my_file.dat')
do_something_else()
session.join()
```

### Configuration

resumable.py supports a subset of the options provided by [resumable.js]:

* `target` The target URL for the multipart POST request (required)
* `chunk_size` The size in bytes of each uploaded chunk of data (default:
  `1*1024*1024`)
* `simultaneous_uploads` Number of simultaneous uploads (default: `3`)
* `headers` Extra headers to include in the multipart POST with data (default:
  `{}`)
* `test_chunks` Make a GET request to the server for each chunks to see if it
  already exists. If implemented on the server-side, this will allow for upload
  resumes even after a browser crash or even a computer restart. (default:
  `True`)

Some additional low level options are available - these are documented in the
docstring of the `Resumable` class.

## Contribute

resumable.py's design is informed by [resumable.js], however only a core subset
of features have yet been implemented. Patches implementing resumable.js
features are welcome, and contributors should attempt to retain consistency
with the resumable.js interface, mapping JavaScript style and idioms to Python
equivalents as appropriate (for example, the `simultaneousUploads`
configuration parameter becomes `simultaneous_uploads` in Python).

[resumable.js]: http://resumablejs.com
