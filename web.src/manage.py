#!/usr/bin/env python3
# vim:fileencoding=UTF-8 
# 
# Copyright © 2015, 2020 Stan Livitski
# 
# Licensed under the Apache License, Version 2.0 with modifications
# and the "Commons Clause" Condition, (the "License"); you may not
# use this file except in compliance with the License. You may obtain
# a copy of the License at
# 
#  https://raw.githubusercontent.com/StanLivitski/cards.webapp/master/LICENSE
# 
# The grant of rights under the License will not include, and the License
# does not grant to you, the right to Sell the Software, or use it for
# gambling, with the exception of certain additions or modifications
# to the Software submitted to the Licensor by third parties.
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from collections import abc
import errno
import os
import random
import re
import socket
import socketserver
import sys


import django.core.management
from django.core.management.commands import runserver
from django.core.servers import basehttp

RE_PORT = re.compile(r'\d+$')
default_port = 8778

class ManagementUtility(django.core.management.ManagementUtility):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_ = None

    def fetch_command(self, *args, **kwargs):
        self.command_ = super().fetch_command(*args, **kwargs)
        return self.command_

utility = ManagementUtility(sys.argv)

class PortChanger(abc.Callable):
    def __init__(self, method, retries = 10, hop = 10):
        assert callable(method)
        self.method = method
        assert 0 < retries
        self.retries = retries
        assert 0 < hop <= default_port / retries
        self.hop = hop
        self.busy = set()
        self.port = None

    def _hop(self, port):
        self.busy.add(port)
        incr = random.randrange(-self.hop, self.hop)
        incr += (1 if 0 <= incr else 0)
        port += incr
        while port in self.busy:
            port -= int(incr / abs(incr))
        return port

    def __call__(self, addr, port, *args, **kwargs):
        stdout = utility.command_.stdout if utility.command_ else sys.stdout
        while True:
            try:
                return self.method(addr, port, *args, **kwargs)
            except socket.error as e:
                if e.errno == errno.EACCES:
                    stdout.write("No access to port %d, retrying ..." % port)                    
                elif e.errno == errno.EADDRINUSE:
                    stdout.write("Port %d busy, retrying ..." % port)
                else:                    
                    raise
                if 0 >= self.retries:
                    raise
                self.retries -= 1
                self.port = port = self._hop(port)
                stdout.write("Starting development server at http://%s:%s/"
                      % (addr, port))

class Prompter(abc.Callable):
    def __init__(self, obj, method):
        self.method = getattr(obj, method)
        self.restore = (obj, method)

    def __call__(self, *args, **kwargs):
        command = utility.command_
        if command:
            stdout = command.stdout
            protocol = command.protocol
            addr = '[%s]' % command.addr if command._raw_ipv6 else command.addr
            port = basehttp.run.port if isinstance(basehttp.run, PortChanger) else None
            port = port or command.port
            ports = { 'https': 443, 'http': 80 }
            suffix = '' if port == ports.get(protocol) else ':%s' % port
            if addr == ('[::]' if command.use_ipv6 else '0.0.0.0'):
                addr = '[::1]' if command.use_ipv6 else '127.0.0.1'
            stdout.write(
                '\nTo start a game, point your browser at\n %s://%s%s/\n'
                'To allow remote players to join, open port %s on your firewall,\n'
                'e.g. on Linux:\n'
                ' sudo %s -A INPUT -p tcp -m tcp --dport %s -j ACCEPT\n'
                '(the above command may need changes to work with existing\n'
                ' iptables configuration or limit remote players\' addresses)\n\n'
                % (protocol, addr, suffix, port,
                   'ip6tables' if command.use_ipv6 else 'iptables', port)
            )
        setattr(*self.restore, self.method)
        return self.method(*args, **kwargs)

def defaultServer(command):
    command = command.lower()
    if '.py' == command[-3:]:
        command = command[:-3]
    if 'runserver' != command:
        return
    sys.argv[0] = command
    os.environ["DJANGO_SETTINGS_MODULE"] = "cards_web.settings"
    fixport = v6 = False
    addrport = None
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg.lower() == '--fixport':
            fixport = True
            sys.argv.pop(i)
        elif arg == '--':
            i += 1
            if i < len(sys.argv):
                addrport = sys.argv[i]
            break
        elif not arg.startswith('-'):
            addrport = arg
        elif arg == '--ipv6' or arg == '-6':
            v6 = True 
    sys.argv.insert(1, '--noreload')
    sys.argv.insert(0, realpath)
    if not fixport:
        import importlib
        basehttp.run = PortChanger(basehttp.run)
        importlib.reload(runserver)
    runserver.Command.default_port = default_port
    default_addr = '0.0.0.0'
    if hasattr(runserver.Command, 'default_addr'):
        setattr(runserver.Command, 'default_addr', default_addr)
    elif v6:
        pass
    elif not addrport:
        addrport = '%s:%s' % (default_addr, runserver.Command.default_port)
        sys.argv.append(addrport)
    elif RE_PORT.match(addrport):
        sys.argv.remove(addrport)
        addrport = default_addr + ':' + addrport
        sys.argv.append(addrport)
    default_addr = '::'
    if hasattr(runserver.Command, 'default_addr_ipv6'):
        setattr(runserver.Command, 'default_addr_ipv6', default_addr)
    elif not v6:
        pass
    elif not addrport:
        addrport = '%s:%s' % (default_addr, runserver.Command.default_port)
        sys.argv.append(addrport)
    elif RE_PORT.match(addrport):
        sys.argv.remove(addrport)
        addrport = default_addr + ':' + addrport
        sys.argv.append(addrport)
    prompter = Prompter(
        socketserver.BaseServer,
        'serve_forever'
    )
    def patch(self, *args, **kwargs):
        prompter(self, *args, **kwargs)
    socketserver.BaseServer.serve_forever = patch

if __name__ == "__main__":

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cards_web.settings")

    basedir, command = os.path.split(os.path.abspath(__file__))
    realpath = os.path.realpath(__file__)
    projdir = os.path.dirname(realpath)
    defaultServer(command)
    if not os.path.samefile(basedir, projdir):
        addpath = []
        for entry in os.listdir(basedir):
            if '.src' == entry[-4:].lower():
                entry = os.path.join(basedir, entry)
                if os.path.isdir(entry) and (
                     not sys.path or
                     not os.path.samefile(entry, os.path.abspath(sys.path[0]))
                    ):
                    sys.path.insert(0, entry)
                    addpath.insert(0, entry)
        if addpath:
            if 'PYTHONPATH' in os.environ:
                addpath.append(os.environ['PYTHONPATH'])
            os.environ['PYTHONPATH'] = os.pathsep.join(addpath)

    if not 'DJANGO_SECRET_KEY' in os.environ:
        import string
        os.environ['DJANGO_SECRET_KEY'] = ''.join(
            [ random.SystemRandom().choice(
                "{}{}{}".format(string.ascii_letters, string.digits, string.punctuation))
                for i in range(63)
            ])

    utility.execute()
