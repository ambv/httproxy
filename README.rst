httproxy
========

This module implements a tiny HTTP proxy by extending ``BaseHTTPServer``.
Supports the ``GET``, ``HEAD``, ``POST``, ``PUT``, ``DELETE`` and ``CONNECT``
methods.

The latest version can be installed via `PyPI
<http://pypi.python.org/pypi/httproxy/>`_::

  $ pip install httproxy
  
or::

  $ easy_install httproxy


The `source code repository <http://github.com/ambv/httproxy>`_ and `issue
tracker <http://github.com/ambv/httproxy/issues>`_ are maintained on
`GitHub <http://github.com/ambv/httproxy>`_.


Quickstart 
----------

Usage::

  httproxy [options]
  httproxy [options] <allowed-client> ...

Options::

  -h, --help                   Show this screen.
  --version                    Show version and exit.
  -H, --host HOST              Host to bind to [default: 127.0.0.1].
  -p, --port PORT              Port to bind to [default: 8000].
  -l, --logfile PATH           Path to the logfile [default: STDOUT].
  -i, --pidfile PIDFILE        Path to the pidfile [default: httproxy.pid].
  -d, --daemon                 Daemonize (run in the background). The
                               default logfile path is httproxy.log in
                               this case.
  -c, --configfile CONFIGFILE  Path to a configuration file.
  -v, --verbose                Log headers.

To start the proxy server and bind it to port 22222 (the port on which it will
listen and accept connections)::

    httproxy -p 22222

To start the proxy server, bind it to port 22222 and tell it to log all requests
to the file ``httproxy.log``::

    httproxy -p 22222 -l httproxy.log

To start the proxy server so it only allows connections from IP
``123.123.123.123``::

    httproxy 123.123.123.123

To start the proxy server bound to port 22222, log to file ``httproxy.log`` and run
the server in the background (as a daemon)::

    httproxy -p 22222 -l httproxy.log -d


Configuration file
------------------

Every option stated as a command-line argument can be passed using
a configuration file. httproxy looks for the following files to read
configuration:

* ``/etc/httproxy/config``

* ``$HOME/.httproxy/config`` (or ``%HOME%\.httproxy\config`` on Windows)

* the value specified in ``--configfile`` on command-line

The names of the settings in the ``main`` section are derived from the long
command line option names.

The ``allowed-clients`` section holds a list of hostnames that can access the
proxy, one hostname per line. Remove this section or leave empty to allow any
client to connect.

An example file::

  [main]
  host = localhost
  port = 8011
  logfile = /Users/ambv/.httproxy/log
  pidfile = /Users/ambv/.httproxy/pid
  daemon = yes
  verbose = yes

  [allowed-clients]
  localhost
  192.168.0.1

**Note:** command-line options have precedence over configuration file settings.


Optional dependencies
---------------------

If you install ``setproctitle``, the name of the process reported by ``ps`` will
be more descriptive.

If you install ``psutil``, httproxy will be able to automatically remove stale
pidfiles on startup.


Change Log
----------

0.9.0
~~~~~

* ability to read configuration from a file (``--configfile``)

* ability to specify the address the proxy will bind to (``--host``)

* ability to log headers sent and received (``--verbose``)

* better process management: pidfile support, a more descriptive process title
  (with the optional ``setproctitle`` dependency)

* fixed spurious ``[Errno 54] Connection reset by peer`` tracebacks

* properly shuts down when receiving ``SIGHUP``, ``SIGINT`` or ``SIGTERM``

* major code refactoring

* compatible with Python 2.6 and 2.7 only: requires ``docopt`` and ``configparser``

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
