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
import os
import sys

if __name__ == "__main__":

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cards_web.settings")

    basedir, command = os.path.split(os.path.abspath(__file__))
    realpath = os.path.realpath(__file__)
    projdir = os.path.dirname(realpath)
    command = command.lower()
    if '.py' == command[-3:]:
        command = command[:-3]
        if 'runserver' == command:
            sys.argv[0] = command
#            sys.argv.insert(1, '--noreload')
            sys.argv.insert(0, realpath)

    if not os.path.samefile(basedir, projdir) and len(sys.argv) > 1:
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
        import random, string
        os.environ['DJANGO_SECRET_KEY'] = ''.join(
            [ random.SystemRandom().choice(
                "{}{}{}".format(string.ascii_letters, string.digits, string.punctuation))
                for i in range(63)
            ])

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
