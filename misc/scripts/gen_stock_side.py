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
Command-line tool for generating SVG images of a stock's side.

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

See also
--------

make_svg : Command-line entry point of the tool. See PyDoc comment
    for specification.
"""
import sys

if 'version_info' not in dir(sys) or sys.version_info[0] < 3 or (
     sys.version_info[0] == 3 and sys.version_info[1] < 2):
    sys.stderr.write('This program requires Python version 3.2 or newer.\n')
    sys.exit(1)

import click
import os
import logging

from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesNSImpl

class Generator:

    def __init__(self, out, count, offset):
        self.out = out
        self.count = count
        self.offset = offset + self.strokeWidth
        if self.offset * 2 > self.marginWidth:
            raise Generator.Error(
                'Offsets larger than %g are not supported, got %g'
                % (self.marginWidth / 2. - self.strokeWidth, offset)
            )
        self.log = None

    fillColor = '#fefefe'
    strokeColor = '#000000'
    strokeWidth = 0.5
    marginWidth = 10
    canvasHeight = 318
    edgeShape = "M0.25,10C0.5,4.5,4.5,0.5,10,0.25h.25V317.75H10c-4.5,-0.5,-9.75,-4.5,-10,-10z"

    SVG_NAMESPACE = "http://www.w3.org/2000/svg"
    SVG_ELEMENT = (SVG_NAMESPACE, 'svg')
    SVG_VERSION = '1.1'

    XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
    XLINK_PREFIX = "xlink"
    XLINK_HREF_ATTR = (XLINK_NAMESPACE, 'href')

    X_ATTR = (SVG_NAMESPACE, 'x')

    EDGE_PATH_ID = 'edge'

    def run(self):
        log = logging.getLogger(__name__ + '.'
            + type(self).__name__) if self.log is None else self.log
        log.debug('Running %s to stack edges of %d cards at adjusted offset %f',
                  type(self).__name__, self.count, self.offset)

        xml = XMLGenerator(self.out, 'UTF-8', True)
        xml.startDocument()
        xml.startPrefixMapping('', self.SVG_NAMESPACE)
        xml.startPrefixMapping(self.XLINK_PREFIX, self.XLINK_NAMESPACE)
        canvasWidth = int(self.marginWidth + (self.count - 1) * self.offset)
        attrs = self._defaultNSAttrs({
            self._svgName('version') : self.SVG_VERSION,
            self._svgName('width') : str(canvasWidth),
            self._svgName('height') : str(self.canvasHeight),
            self._svgName('viewBox') : (
                '%d %d %d %g' % (0,0,canvasWidth,self.canvasHeight)
            )
        })
        xml.startElementNS(self.SVG_ELEMENT, None, attrs)
        self._defs(xml)
        self._contentGroup(xml)
        xml.ignorableWhitespace('\n')
        xml.endElementNS(self.SVG_ELEMENT, None)
        xml.endPrefixMapping('')
        xml.endPrefixMapping(self.XLINK_PREFIX)
        xml.endDocument()

    def _edgePathRef(self, xml, offset):
        element = self._svgName('use')
        xml.ignorableWhitespace('\n  ')
        attrs = AttributesNSImpl(
            {
             self.XLINK_HREF_ATTR : '#' + self.EDGE_PATH_ID,
             self.X_ATTR : str(offset)
            },
            {
             self.XLINK_HREF_ATTR :
              self.XLINK_PREFIX + ':' + self.XLINK_HREF_ATTR[1],
             self.X_ATTR : self.X_ATTR[1]
            }
        )
        xml.startElementNS(element, None, attrs)
        xml.endElementNS(element, None)

    def _contentGroup(self, xml):
        element = self._svgName('g')
        xml.ignorableWhitespace('\n ')
        attrs = self._defaultNSAttrs({
            self._svgName('style') : (
                'fill:%s;stroke:%s;stroke-width:%g'
                % (self.fillColor, self.strokeColor, self.strokeWidth)
            ),
        })
        xml.startElementNS(element, None, attrs)
        for i in range(0, self.count):
            self._edgePathRef(xml, i * self.offset)
        xml.ignorableWhitespace('\n ')
        xml.endElementNS(element, None)

    def _edgePath(self, xml):
        element = self._svgName('path')
        xml.ignorableWhitespace('\n  ')
        attrs = self._defaultNSAttrs({
            self._svgName('id') : self.EDGE_PATH_ID,
            self._svgName('d') : self.edgeShape
        })
        xml.startElementNS(element, None, attrs)
        xml.endElementNS(element, None)

    def _defs(self, xml):
        element = self._svgName('defs')
        xml.ignorableWhitespace('\n ')
        xml.startElementNS(element, None, AttributesNSImpl({}, {}))
        self._edgePath(xml)
        xml.ignorableWhitespace('\n ')
        xml.endElementNS(element, None)

    @classmethod
    def _svgName(cls, name):
        return (cls.SVG_NAMESPACE, name)

    @staticmethod
    def _defaultNSAttrs(attrs):
        qnames = { name : name[1] for name in attrs.keys() }
        return AttributesNSImpl(attrs, qnames)

    def _style(self, xml):
        element = self._svgName('style')
        xml.ignorableWhitespace('\n ')
        xml.startElementNS(element, None, AttributesNSImpl({}, {}))
        xml.endElementNS(element, None)

    class Error(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def __repr__(self):
            return '%s.%s %s' % (type(Generator).__name__,
                                type(self).__name__,
                                self)

@click.command()
@click.option('-n', '--count', default = 22,
              help='The number of cards in the stock.')
@click.option('-d', '--offset', default = .75,
              help='The visible distance between cards\' edges.')
@click.argument('target', required=False,
                type=click.Path(
                 dir_okay=False,
                 writable=True,
                 resolve_path=True
                ))
@click.option('-v', '--verbose', count=True,
              help='Repeat up to 2 times for additional debug info on stderr.')
@click.option('-q', '--quiet', is_flag=True,
              help='Suppresses progress message(s) on the standard error.')
@click.option('-f', '--force', is_flag=True,
              help='Overwrite any existing target file.')
def make_svg(count, offset, target, verbose, quiet, force):
    """
    Creates an SVG image of a stock's side.

    Arguments:
    
    \b
     - TARGET the file to receive the resulting image
       (defaults to the standard output if omitted) 
    """

    if quiet:
        logging.basicConfig(level = logging.WARN) 
    else:
        logging.basicConfig(level =
            (logging.INFO, logging.DEBUG, 1)[verbose])
    log = logging.getLogger(__name__)

    out = None 
    if target is None:
        pass
    elif os.path.exists(target) and not force:
        log.error(
            ('File "%s" already exists.'
             + 'Delete it first, or use option -f to overwrite.'
            ) % target
        )
        sys.exit(2)
    else:
        out = open(target, 'w', 1, 'utf_8')

    try:
        maker = Generator(out, count, offset)
        maker.log = log
        maker.run()
    except:
        error = sys.exc_info()
        if isinstance(error[1], Generator.Error):
            if 1 < verbose:
                log.error('Could not write the image', exc_info = error)
            else:
                log.error('Could not write the image: %s', error[1])
            sys.exit(4)
        else:
            if 0 < verbose:
                log.error('', exc_info = error)
            else:
                log.error('%s: %s', error[0].__name__, error[1])
            sys.exit(3)
    finally:
        if out is None:
            log.info(
                'Wrote SVG output to standard out, run with --help for usage details.')
        else:
            out.close()

if __name__ == '__main__':
    make_svg()
