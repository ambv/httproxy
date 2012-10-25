proxy
=====

This module implements ``GET``, ``HEAD``, ``POST``, ``PUT``, ``DELETE`` and
``CONNECT`` methods on ``BaseHTTPServer``.

The latest version can be installed via `PyPI
<http://pypi.python.org/pypi/proxy/>`_::

  $ pip install proxy
  
or::

  $ easy_install proxy


The `source code repository <http://github.com/ambv/proxy>`_ and `issue
tracker <http://github.com/ambv/proxy/issues>`_ are maintained on
`GitHub <http://github.com/ambv/proxy>`_.


Usage examples
--------------

Available command-line arguments::

    proxy [-p port] [-l logfile] [-dh] [allowed_client_name ...]]

    -p       - Port to bind to
    -l       - Path to logfile. If not specified, STDOUT is used
    -d       - Run in the background

To start the proxy server and bind it to port 22222 (the port on which it will
listen and accept connections)::

    proxy -p 22222

To start the proxy server, bind it to port 22222 and tell it to log all requests
to the file ``proxy.log``::

    proxy -p 22222 -l proxy.log

To start the proxy server so it only allows connections from IP
``123.123.123.123``::

    proxy 123.123.123.123

To start the proxy server bound to port 22222, log to file ``proxy.log`` and run
the server in the background (as a daemon)::

    proxy -p 22222 -l proxy.log -d


Change Log
----------

0.3.1
~~~~~

* added rudimentary FTP file retrieval

* added custom logging methods

* added code to make it run as a standalone application

Upgraded by `Mitko Haralanov
<http://www.voidtrance.net/2010/01/simple-python-http-proxy/>`_ in 2009.

0.2.1
~~~~~

* basic version hosted in 2006 by the original author at
  http://www.oki-osk.jp/esc/python/proxy/

Authors
-------

Script based on work by Suzuki Hisao and Mitko Haralanov, currently maintained
by `Łukasz Langa <mailto:lukasz@langa.pl>`_.
