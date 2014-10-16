#!/bin/sh -e
if [[ -f pid.local ]]; then
  kill -9 `cat pid.local` || true
  rm -rf pid.local
fi

if [[ $1 == "clean" ]]; then
  rm -rf website.local
  rm -rf proxy.local
  rm -rf client.local
  rm -f log.local
  exit 0
fi

PYTHONWARNINGS=i


if [[ -z "$VIRTUALENV" ]]; then
  for venv in virtualenv virtualenv-2.7 pyvenv-3.4; do
    if which $venv >/dev/null; then
      VIRTUALENV=$venv
      break
    fi
  done
fi
if [[ ! -d website.local ]]; then
  $VIRTUALENV website.local
fi
if [[ ! -d proxy.local ]]; then
  $VIRTUALENV proxy.local
  source proxy.local/bin/activate
  python -c 'import site; print(site.__file__)'
  pip install deps/ordereddict-1.1.tar.gz
  if [[ -z "$SKIP_EXTRAS" ]]; then
    echo "Including extras. (skip installing setproctitle and psutil with SKIP_EXTRAS=1)"
    pip install deps/setproctitle-1.1.8.tar.gz
    pip install deps/psutil-2.1.3.tar.gz
  fi
  pip install deps/docopt-0.6.2.tar.gz
  pip install deps/configparser-3.5.0b2.tar.gz
  cd ..
  pip install -e .
  cd test
  deactivate
fi
if [[ ! -d client.local ]]; then
  $VIRTUALENV client.local
  source client.local/bin/activate
  python -c 'import site; print(site.__file__)'
  pip install deps/requests-2.4.3-py2.py3-none-any.whl
  deactivate
fi

source website.local/bin/activate
cd ..
python -m SimpleHTTPServer 19191 >/dev/null 2>/dev/null &
httpd_pid=$!
echo httpd running at $httpd_pid
cd test
deactivate

source proxy.local/bin/activate
httproxy --daemon --host localhost --logfile log.local --pidfile pid.local --port 19192 --verbose localhost
echo proxy running at `cat pid.local`
deactivate

source client.local/bin/activate
python client.py || true
deactivate

# teardown

kill -1 $httpd_pid || true
kill -1 `cat pid.local` || true
