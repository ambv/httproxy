#!/bin/sh -e
if [[ -f pid.local ]]; then
  kill `cat pid.local` || true
fi
for venv in virtualenv virtualenv-2.7 virtualenv-2.6; do
  if which $venv >/dev/null; then
    VIRTUALENV=$venv
    break
  fi
done
if [[ ! -d website.local ]]; then
  $VIRTUALENV --no-site-packages --use-distribute website.local
fi
if [[ ! -d proxy.local ]]; then
  $VIRTUALENV --no-site-packages --use-distribute proxy.local
  source proxy.local/bin/activate
  python -c 'import site; print site.__file__'
  pip install deps/ordereddict-1.1.tar.gz
  pip install deps/unittest2-0.5.1.tar.gz
  pip install deps/docopt-0.6.1.tar.gz
  pip install deps/configparser-3.3.0r2.tar.gz
  cd ..
  pip install -e .
  cd test
  deactivate
fi
if [[ ! -d client.local ]]; then
  $VIRTUALENV --no-site-packages --use-distribute client.local
  source client.local/bin/activate
  python -c 'import site; print site.__file__'
  pip install deps/requests-1.1.0.tar.gz
  deactivate
fi

source website.local/bin/activate
cd ..
python -m SimpleHTTPServer 19191 >/dev/null 2>&1 &
httpd_pid=$!
echo httpd running at $httpd_pid
cd test
deactivate

source proxy.local/bin/activate
httproxy --daemon --host localhost --logfile log.local --pidfile pid.local --port 19192 --verbose localhost
deactivate

source client.local/bin/activate
python client.py || true
deactivate

# teardown

kill -1 $httpd_pid
kill -1 `cat pid.local`

if [[ $1 == "clean" ]]; then
  rm -rf website.local
  rm -rf proxy.local 
  rm -rf client.local
  rm -f log.local
fi
