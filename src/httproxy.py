#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2001 - 2012 SUZUKI Hisao, Mitko Haralanov, Łukasz Langa

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Tiny HTTP Proxy.

This module implements GET, HEAD, POST, PUT, DELETE and CONNECT
methods on BaseHTTPServer.

Usage:
  httproxy [options]
  httproxy [options] <allowed-client> ...

Options:
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
"""

__version__ = "0.9.0"

import atexit
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import errno
import ftplib
import logging
import logging.handlers
import os
import re
import select
import signal
import socket
import SocketServer
import sys
import threading
from time import sleep
from types import FrameType, CodeType
import urlparse

from configparser import ConfigParser
from docopt import docopt

DEFAULT_LOG_FILENAME = "httproxy.log"
HEADER_TERMINATOR = re.compile(r'\r\n\r\n')


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "TinyHTTPProxy/" + __version__
    protocol = "HTTP/1.0"
    rbufsize = 0                        # self.rfile Be unbuffered
    allowed_clients = ()
    verbose = False
    cache = False

    def handle(self):
        ip, port = self.client_address
        self.server.logger.log(logging.DEBUG, "Request from '%s'", ip)
        if self.allowed_clients and ip not in self.allowed_clients:
            self.raw_requestline = self.rfile.readline()
            if self.parse_request():
                self.send_error(403)
        else:
            BaseHTTPRequestHandler.handle(self)

    def _connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i + 1:])
        else:
            host_port = netloc, 80
        self.server.logger.log(
            logging.DEBUG, "Connect to %s:%d", host_port[0], host_port[1])
        try:
            soc.connect(host_port)
        except socket.error, arg:
            try:
                msg = arg[1]
            except Exception:
                msg = arg
            self.send_error(404, msg)
            return 0
        return 1

    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(self.path, soc):
                self.log_request(200)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self._read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):
        scm, netloc, path, params, query, fragment = urlparse.urlparse(
            self.path, 'http')
        if scm not in ('http', 'ftp') or fragment or not netloc:
            self.send_error(400, "bad URL %s" % self.path)
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if scm == 'http':
                if self._connect_to(netloc, soc):
                    self.log_request()
                    soc.send("%s %s %s\r\n" % (
                        self.command, urlparse.urlunparse(
                            ('', '', path, params, query, '')),
                        self.request_version,
                    ))
                    self.headers['Connection'] = 'close'
                    del self.headers['Proxy-Connection']
                    for key_val in self.headers.items():
                        self.log_verbose("%s: %s", *key_val)
                        soc.send("%s: %s\r\n" % key_val)
                    soc.send("\r\n")
                    self._read_write(soc)
            elif scm == 'ftp':
                # fish out user and password information
                i = netloc.find('@')
                if i >= 0:
                    login_info, netloc = netloc[:i], netloc[i + 1:]
                    try:
                        user, passwd = login_info.split(':', 1)
                    except ValueError:
                        user, passwd = "anonymous", None
                else:
                    user, passwd = "anonymous", None
                self.log_request()
                try:
                    ftp = ftplib.FTP(netloc)
                    ftp.login(user, passwd)
                    if self.command == "GET":
                        ftp.retrbinary("RETR %s" % path, self.connection.send)
                    ftp.quit()
                except Exception, e:
                    self.server.logger.log(
                        logging.WARNING, "FTP Exception: %s", e
                    )
        finally:
            soc.close()
            self.connection.close()

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except socket.error, e:
            if e.errno == errno.ECONNRESET:
                pass   # ignore the error
            else:
                raise

    def _read_write(self, soc, max_idling=20):
        iw = [self.connection, soc]
        local_data = []
        ow = []
        count = 0
        while True:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 1)
            if exs:
                break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    if data:
                        if self.cache or self.verbose:
                            local_data.append(data)
                        out.send(data)
                        count = 0
            if count == max_idling:
                break
        result = "".join(local_data)
        if self.verbose:
            ht = HEADER_TERMINATOR.search(result)
            if ht:
                headers = result[:ht.span()[0]].split('\n')
                for header in headers:
                    header = header.strip()
                    self.log_verbose("[response] %s", header)
        return result

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET

    def log_verbose(self, fmt, *args):
        if not self.verbose:
            return
        self.server.logger.log(
            logging.DEBUG, "%s %s", self.address_string(), fmt % args
        )

    def log_message(self, fmt, *args):
        self.server.logger.log(
            logging.INFO, "%s %s", self.address_string(), fmt % args
        )

    def log_error(self, fmt, *args):
        self.server.logger.log(
            logging.ERROR, "%s %s", self.address_string(), fmt % args
        )


class ThreadingHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, logger=None):
        HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.logger = logger


def setup_logging(filename, log_size, daemon, verbose):
    logger = logging.getLogger("TinyHTTPProxy")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not filename or filename in ('-', 'STDOUT'):
        if not daemon:
            # display to the screen
            handler = logging.StreamHandler()
        else:
            handler = logging.handlers.RotatingFileHandler(
                DEFAULT_LOG_FILENAME, maxBytes=(log_size * (1 << 20)),
                backupCount=5
            )
    else:
        handler = logging.handlers.RotatingFileHandler(
            filename, maxBytes=(log_size * (1 << 20)), backupCount=5)
    fmt = logging.Formatter("[%(asctime)-12s.%(msecs)03d] "
                            "%(levelname)-8s %(threadName)s  "
                            "%(message)s",
                            "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    logger.addHandler(handler)
    return logger


def signal_handler(signo, frame):
    while frame and isinstance(frame, FrameType):
        if frame.f_code and isinstance(frame.f_code, CodeType):
            if "run_event" in frame.f_code.co_varnames:
                frame.f_locals["run_event"].set()
                return
        frame = frame.f_back


def daemonize(logger):
    class DevNull(object):
        def __init__(self):
            self.fd = os.open(os.devnull, os.O_WRONLY)

        def write(self, *args, **kwargs):
            return 0

        def read(self, *args, **kwargs):
            return 0

        def fileno(self):
            return self.fd

        def close(self):
            os.close(self.fd)

    class ErrorLog(object):
        def __init__(self, obj):
            self.obj = obj

        def write(self, string):
            self.obj.log(logging.ERROR, string)

        def read(self, *args, **kwargs):
            return 0

        def close(self):
            pass

    if os.fork() != 0:
        # allow the child pid to instantiate the server class
        sleep(1)
        sys.exit(0)
    os.setsid()
    fd = os.open(os.devnull, os.O_RDONLY)
    if fd != 0:
        os.dup2(fd, 0)
        os.close(fd)
    null = DevNull()
    log = ErrorLog(logger)
    sys.stdout = null
    sys.stderr = log
    sys.stdin = null
    fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(sys.stdout.fileno(), 1)
    if fd != 2:
        os.dup2(fd, 2)
    if fd not in (1, 2):
        os.close(fd)


def set_process_title(args):
    try:
        import setproctitle
    except ImportError:
        return
    proc_details = ['httproxy']
    for arg, value in sorted(args.items()):
        if value is True:
            proc_details.append(arg)
        elif value in (False, None):
            pass   # don't include false or empty toggles
        elif arg == '<allowed-client>':
            for client in value:
                proc_details.append(client)
        else:
            value = unicode(value)
            if 'file' in arg and value not in ('STDOUT', '-'):
                value = os.path.realpath(value)
            proc_details.append(arg)
            proc_details.append(value)
    setproctitle.setproctitle(" ".join(proc_details))


def handle_pidfile(pidfile, logger):
    pid = str(os.getpid())
    try:
        with open(pidfile) as pf:
            stale_pid = pf.read()
        if pid != stale_pid:
            try:
                import psutil
                if psutil.pid_exists(int(stale_pid)):
                    msg = ("Pidfile `%s` exists. PID %s still running. "
                           "Exiting." % (pidfile, stale_pid))
                    logger.log(logging.CRITICAL, msg)
                    raise RuntimeError(msg)
                msg = ("Removed stale pidfile `%s` with non-existing PID %s."
                       % (pidfile, stale_pid))
                logger.log(logging.WARNING, msg)
            except (ImportError, ValueError):
                msg = "Pidfile `%s` exists. Exiting." % pidfile
                logger.log(logging.CRITICAL, msg)
                raise RuntimeError(msg)
    except IOError:
        with open(pidfile, 'w') as pf:
            pf.write(pid)
    atexit.register(os.unlink, pidfile)


def handle_configuration():
    default_args = docopt(__doc__, argv=(), version=__version__)
    cmdline_args = docopt(__doc__, version=__version__)
    for a in default_args:
        if cmdline_args[a] == default_args[a]:
            del cmdline_args[a]   # only keep overriden values
    del default_args['<allowed-client>']
    inifile = ConfigParser(allow_no_value=True)
    inifile.optionxform = lambda o: o if o.startswith('--') else ('--' + o)
    inifile['DEFAULT'] = default_args
    inifile['allowed-clients'] = {}
    read_from = inifile.read([
        os.sep + os.sep.join(('etc', 'httproxy', 'config')),
        os.path.expanduser(os.sep.join(('~', '.httproxy', 'config'))),
        cmdline_args.get('--configfile') or '',
    ])
    iniconf = dict(inifile['main'])
    for opt in iniconf:
        try:
            iniconf[opt] = inifile['main'].getboolean(opt)
            continue
        except (ValueError, AttributeError):
            pass   # not a boolean
        try:
            iniconf[opt] = inifile['main'].getint(opt)
            continue
        except (ValueError, TypeError):
            pass   # not an int
    iniconf.update(cmdline_args)
    if not iniconf.get('<allowed-client>'):
        # copy values from INI but don't include --port etc.
        inifile['DEFAULT'].clear()
        clients = []
        for client in inifile['allowed-clients']:
            clients.append(client[2:])
        iniconf['<allowed-client>'] = clients
    return read_from, iniconf


def main():
    max_log_size = 20
    run_event = threading.Event()
    read_from, args = handle_configuration()
    logger = setup_logging(
        args['--logfile'], max_log_size, args['--daemon'], args['--verbose'],
    )
    for path in read_from:
        logger.log(logging.DEBUG, 'Read configuration from `%s`.' % path)
    try:
        args['--port'] = int(args['--port'])
        if not (0 < args['--port'] < 65536):
            raise ValueError("Out of range.")
    except (ValueError, TypeError):
        msg = "`%s` is not a valid port number. Exiting." % args['--port']
        logger.log(logging.CRITICAL, msg)
        return 1
    if args['--daemon']:
        daemonize(logger)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if args['<allowed-client>']:
        allowed = []
        for name in args['<allowed-client>']:
            try:
                client = socket.gethostbyname(name)
            except socket.error, e:
                logger.log(logging.CRITICAL, "%s: %s. Exiting." % (name, e))
                return 3
            allowed.append(client)
            logger.log(logging.INFO, "Accept: %s(%s)" % (client, name))
        ProxyHandler.allowed_clients = allowed
    else:
        logger.log(logging.INFO, "Any clients will be served...")
    ProxyHandler.verbose = args['--verbose']
    try:
        handle_pidfile(args['--pidfile'], logger)
    except RuntimeError:
        return 2
    set_process_title(args)
    server_address = socket.gethostbyname(args['--host']), args['--port']
    httpd = ThreadingHTTPServer(server_address, ProxyHandler, logger)
    sa = httpd.socket.getsockname()
    logger.info("Serving HTTP on %s:%s" % (sa[0], sa[1]))
    atexit.register(logger.log, logging.INFO, "Server shutdown")
    req_count = 0
    while not run_event.isSet():
        try:
            httpd.handle_request()
            req_count += 1
            if req_count == 1000:
                logger.log(
                    logging.INFO, "Number of active threads: %s",
                    threading.activeCount()
                )
                req_count = 0
        except select.error, e:
            if e[0] == 4 and run_event.isSet():
                pass
            else:
                logger.log(logging.CRITICAL, "Errno: %d - %s", e[0], e[1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
