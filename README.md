# Resumable.py

[![Build Status](https://travis-ci.org/acroz/resumable.py.svg?branch=master)](https://travis-ci.org/acroz/resumable.py)

Resumable.py provides chunked uploading of files to a compatible server,
emulating the popular [Resumable.js] JavaScript library.

## Contribute

Resumable.py's design is informed by [Resumable.js], however only a core subset
of features have yet been implemented. Patches implementing Resumable.js
features are welcome, and contributors should attempt to retain consistency
with the Resumable.js interface, mapping JavaScript style and idioms to Python
equivalents as appropriate (for example, the `simultaneousUploads`
configuration parameter becomes `simultaneous_uploads` in Python).

[Resumable.js]: http://resumablejs.com
