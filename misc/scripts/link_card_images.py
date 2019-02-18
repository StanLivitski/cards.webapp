#!/usr/bin/env python
# vim:fileencoding=UTF-8 
################################
# Copyright © 2017 Stan Livitski
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
# 
"""
Command-line tool for setting up links to static images of
playing cards.

Dependenices
------------

+-----------------------------------------------------------+---------------+
|  Name / Download URL                                      | Version       |
+===========================================================+===============+
| | Python                                                  | 3.2 or newer  |
| | https://www.python.org/downloads/ or an OS distribution |               |
+-----------------------------------------------------------+---------------+
| | ``click`` package                                       | 6.3 or newer  |
| | https://pypi.python.org/pypi/click or                   |               |
| | http://click.pocoo.org/                                 |               |
+-----------------------------------------------------------+---------------+
| | ``cards.webapp`` project                                | any available |
| | https://github.com/StanLivitski/cards.webapp            |               |
+-----------------------------------------------------------+---------------+

See also
--------

make_links : Command-line entry point of the tool. See PyDoc comment
    for specification.
"""
import sys

if 'version_info' not in dir(sys) or sys.version_info[0] < 3 or (
     sys.version_info[0] == 3 and sys.version_info[1] < 2):
    sys.stderr.write('This program requires Python version 3.2 or newer.\n')
    sys.exit(1)

import click
import os
import abc
import logging

import cards

class LinkMaker(metaclass=abc.ABCMeta):

    def __init__(self, source, target = None):
        self.source = source
        self.target = os.getcwd() if target is None else target
        self.log = None
        self.error = None

    def run(self):
        log = logging.getLogger(__name__ + '.'
            + type(self).__name__) if self.log is None else self.log
        log.debug('Running %s to "%s" in "%s"',
                  type(self).__name__, self.source, self.target)

        self.start()

        realSource = os.path.realpath(self.source)
        for at, dirs, files in os.walk(self.source,
                                followlinks=True,
                                onerror=self._walkError):
            idir = 0
            while len(dirs) > idir:
                dir_ = os.path.join(at, dirs[idir])
                realDir = os.path.realpath(dir_)
                if os.path.commonprefix([realDir, realSource]) == realDir:
                    log.info(
                        'Skipped the symlink loop in source files at: %s',
                        dir_
                    )
                    del dirs[idir]
                else:
                    idir += 1
            del idir

            for file in files:
                path = os.path.join(at, file)
                if self.filter(path):
                    self.link(path)
                else:
                    log.info(
                         'Skipped file "%s" that does not match any card',
                         path
                    )


        self.finish()

    def start(self):
        pass

    def filter(self, path):
        return False

    @abc.abstractmethod
    def link(self, path):
        print(path)

    def finish(self):
        if self.error is not None:
            raise self.error

    def _walkError(self, error):
        raise error

    def warning(self, *args):
        self.log.warning(*args)
        if self.error is None:
            self.error = self.Error(
                'finished with warnings, please review the output above'
            )

    class Error(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.file = kwargs.pop('path', None)

        def __repr__(self):
            return '%s.%s %s' % (type(LinkMaker).__name__,
                                type(self).__name__,
                                self)

        def __str__(self):
            if type(self.file) is str:
                message = 'at "%s"' % self.file
            else:
                return super().__str__()
            if 0 < len(self.args):
                message = '%s %s' % (self.args[0], message)
            return repr((message,) + self.args[1:])

class FrontLinkMaker(LinkMaker):

    def __init__(self, source, target = None, tweakDeck = None):
        super().__init__(source, target)
        self.tweak = tweakDeck

    def start(self):
        super().start()
        source = cards.SimpleDeckFactory(jokers=0).makeDeck()
        self.deck = { card.code : card for card in source }
        if self.tweak is not None:
            self.deck = self.tweak(self.deck)

    def filter(self, path):
        name = os.path.basename(path).upper()
        if not name.endswith('.SVG'):
            return False
        name = name[0:-4]
        return name in self.deck

    def link(self, path):
        name = os.path.basename(path).upper()
        if name.endswith('.SVG'):
            name = name[0:-4]
        card = self.deck[name]
        del self.deck[name]
        link = os.path.relpath(path, self.target)
        to = os.path.join(self.target, card.code + '.svg')
        self.log.log(1, 'Linking "%s" -> "%s"', link, to)
        if os.path.lexists(to):
            self.warning(
                'Skipped existing file in the target directory: %s',
                to
            )
        else:
            os.symlink(link, to)

    def finish(self):
        if self.deck:
            self.warning(
                'Could not find images for the following cards: %s',
                list(self.deck.keys())
            )
        super().finish()

class BackLinkMaker(LinkMaker):

    def __init__(self, source, target = None, prefix = ''):
        super().__init__(source, target)
        self.prefix = prefix

    def filter(self, path):
        name = os.path.basename(path)
        if not name.upper().endswith('.SVG'):
            return False
        name = name[0:-4]
        return name.startswith(self.prefix)

    def link(self, path):
        name = os.path.basename(path)
        name = name[len(self.prefix):]
        if name.upper().endswith('.SVG'):
            name = name[0:-4]
        link = os.path.relpath(path, self.target)
        to = os.path.join(self.target, name + '.svg')
        self.log.log(1, 'Linking "%s" -> "%s"', link, to)
        if os.path.lexists(to):
            self.warning(
                'Skipped existing file in the target directory: %s',
                to
            )
        else:
            os.symlink(link, to)

@click.command()
@click.option('-f', '--front', 'imgtype', flag_value='front',
              help='Make links to front images of cards.')
@click.option('-b', '--back', 'imgtype', flag_value='back',
              help='Make links to images of card backs.')
@click.option('--prefix', 'prefix', default='back_',
              help='Prefix used with names of card backs\'\
 image files.')
@click.argument('source', required=False,
                type=click.Path(
                 exists=True,
                 file_okay=False,
                 readable=True,
                 resolve_path=True
                ))
@click.argument('target', required=False,
                type=click.Path(
                 file_okay=False,
                 writable=True,
                 resolve_path=True
                ))
@click.option('-v', '--verbose', count=True,
              help='Repeat up to 3 times for additional debug info on stderr.')
def make_links(imgtype, source, target, verbose, prefix):
    """
    Creates links to files with images of cards to follow
    this application's naming scheme.

    Arguments:
    
    \b
     - SOURCE directory with image files (required)
     - TARGET directory where links will be made
       (defaults to the current dir if omitted) 
    """

    if 0 < verbose:
        logging.basicConfig(level =
            (logging.INFO, logging.DEBUG, 1)[verbose - 1])
    log = logging.getLogger(__name__)

    if imgtype is None:
        log.error(
            'One of the --front, --back, or --help options is required.'
            + ' Use --help option to get the details.'
        )
        sys.exit(2)
    elif source is None:
        log.error(
            'Source directory argument is required.'
            + ' Use --help option to get the details.'
        )
        sys.exit(2)
    elif 'front' == imgtype:
        def tweak(deck):
            changes = dict()
            for code in deck:
                card = deck[code]
                if card.rank == 'ace':
                    changes[code] = '1' + code[1:]
            for code in changes:
                card = deck[code]
                del deck[code]
                deck[changes[code]] = card
            return deck
        maker = FrontLinkMaker(source, target, tweak)
    elif 'back' == imgtype:
        maker = BackLinkMaker(source, target, prefix)
    else:
        log.error(
            'Unsupported mode: %s' % imgtype
        )
        sys.exit(2)

    try:
        maker.log = log
        maker.run()
    except:
        error = sys.exc_info()
        if isinstance(error[1], LinkMaker.Error):
            if 1 < verbose:
                log.error('Problem linking source images', exc_info = error)
            else:
                log.error('Problem linking images: %s', error[1])
            sys.exit(4)
        else:
            if 1 < verbose:
                log.error('', exc_info = error)
            else:
                log.error('%s: %s', type(error[0]).__name__, error[1])
            sys.exit(3)

if __name__ == '__main__':
    make_links()
