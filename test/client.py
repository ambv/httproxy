#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import os.path
import requests

directory = os.path.realpath(os.path.dirname(__file__))
test_content = os.sep.join((directory, 'content.local'))

with open(test_content, 'w') as w:
    w.write('Test content.')

req = requests.get('http://localhost:19191/test/content.local')
assert req.status_code == 200

req = requests.get('http://localhost:19191/test/content.local',
                   proxies={'http': 'http://localhost:19192'})
assert req.status_code == 200

os.unlink(test_content)

req = requests.get('http://localhost:19191/test/content.local')
assert req.status_code == 404

req = requests.get('http://localhost:19191/test/content.local',
                   proxies={'http': 'http://localhost:19192'})
assert req.status_code == 404

print "All tests passed."
