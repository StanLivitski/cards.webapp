# vim:fileencoding=UTF-8 
#
# Copyright © 2019 Stan Livitski
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
import io
import collections
import logging
import math
import os
import re
import sys
import xml.sax
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesNSImpl

from django.conf import settings
from django.http.response import HttpResponse, HttpResponseNotFound, \
    HttpResponseServerError, HttpResponsePermanentRedirect # , StreamingHttpResponse
from django.shortcuts import render
from django.utils.cache import patch_response_headers
from django.utils.http import urlencode   
from django.views.generic import View
from xml.sax._exceptions import SAXParseException
from builtins import setattr

"""
    Renderers of the game pages' dynamic elements.
    
    TODOdoc: <Extended description>

    Key elements
    ------------
    <python_name> : <One-line summary of a class, exception,
    function, or any other object exported by the module and
    named on this line.>
    <The docstring for a package's ``__init__`` module should,
    in most cases list the modules and subpackages exported by
    the package here. >
    ...

[    See Also
    --------
    <python_name> : <Description of code named on this line
    and how it is related to the documented module.>
    ... ]

[    Notes
    ----------
    <Additional information about the code, possibly including
    a discussion of the algorithm. Follow it with a 'References'
    section if citing any references.>
    ]

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
"""

def dimmer_view(request, style):
    response = render(
                request,
                'durak/table/dimmer.svg',
                {'style':style},
                content_type='image/svg+xml'
            )
    patch_response_headers(response)
    return response

class SVGView(View):

    http_method_names = [ 'get' ]

    SVG_NAMESPACE = "http://www.w3.org/2000/svg"
    SVG_ELEMENT = SVG_NAMESPACE, 'svg'
    XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
    XLINK_HREF_ATTR = XLINK_NAMESPACE, 'href'

    ATTRS_SVG_DIMENSION = 'width', 'height'

class StockSideView(SVGView):
    """
    Render an SVG image of a stock's side.
    
    TODOdoc? <Extended description>
    
[    Parameters
    --------------------
    <var>[, <var>] : <type | value-list>[, optional]
        <Description of constructor's parameter(s), except ``self``>
    ...]

[    Attributes
    -----------------
    <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

[    Methods
    ---------------
    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

[    See Also
    --------------
    <python_name> : <Description of code referred by this line
    and how it is related to the documented code.>
     ... ]
    """

    def get(self, request, gap):
        '''
        Process a request, taking the count of cards as a parameter.
        '''
        log = logging.getLogger(type(self).__module__)
        count = request.GET.get('count', 22)           
        try:
            count = int(count)
            if not (0 <= count < 250):
                raise ValueError('Count is out of range (0, 250): %d' % count)
            buffer = io.StringIO()
            StockSideGenerator(buffer, count, float(gap) if gap else 1).run()
            return HttpResponse(buffer.getvalue(),
                            content_type='image/svg+xml')
        except:
            log.error('Error painting stacked edges of "%s" cards with gap "%s"',
                      count, gap, exc_info=True)
            return HttpResponseServerError()

class StockSideGenerator:

    for name, value in vars(SVGView).items():
        if not name.startswith('_') and name.upper() == name:
            exec(name + ' = ' + repr(value))

    fillColor = '#fefefe'
    strokeColor = '#000000'
    strokeWidth = 0.5
    marginWidth = 10
    canvasHeight = 318
    edgeShape = "M0.25,10C0.5,4.5,4.5,0.5,10,0.25h.25V317.75H10c-4.5,-0.5,-9.75,-4.5,-10,-10z"

    SVG_VERSION = '1.1'
    XLINK_PREFIX = "xlink"
    X_ATTR = (SVGView.SVG_NAMESPACE, 'x')
    EDGE_PATH_ID = 'edge'

    def __init__(self, out, count, offset = .75):
        self.out = out
        self.count = count
        self.offset = offset + self.strokeWidth
        if self.offset * 2 > self.marginWidth:
            raise ValueError(
                'Offsets larger than %g are not supported, got %g'
                % (self.marginWidth / 2. - self.strokeWidth, offset)
            )

    def run(self):
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
        xml.startElementNS(element, None,
                           AttributesNSImpl({}, {}))
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
        xml.startElementNS(element, None,
                           AttributesNSImpl({}, {}))
        xml.endElementNS(element, None)

class CardBackView(SVGView):
    """
    Render a card back image or a slice thereof.
    

    Methods
    ---------------
    get(django.http.HttpRequest, str)
        Process a GET request, taking the image name as a parameter.

    See Also
    --------------
    ClipFinder : TODOdoc <Description of code referred by this line
    and how it is related to the documented code.>
    ClipExtractor : TODOdoc <Description of code referred by this line
    and how it is related to the documented code.>
    """

    IMAGES_DIR = os.path.join(settings.DEPENDENCIES_DIR, 'backs')
    PATTERN_FILE_NAME = '%s.svg'

    PATTERN_COORDINATE_DELIMITER = re.compile(r'\s*,\s*|\s+')

    def get(self, request, image):
        '''
        Process a request, taking the image name as a parameter.
    
        The image file name, without extension, is received as 
        a URLconf parameter. The other optional parameters are
        obtained from the request. These include ``id`` and
        ``fraction``. If ``id`` is supplied, the request is
        processed in the extraction mode, otherwise it runs
        in the id lookup mode.
        '''
        log = logging.getLogger(type(self).__module__)
        file = os.path.join(self.IMAGES_DIR,
                            self.PATTERN_FILE_NAME % image)
        fraction = 'unknown'
        try:
            if not os.path.exists(file):
                return HttpResponseNotFound()
            if 'id' in request.GET:
                buffer = io.StringIO()
                parser = xml.sax.make_parser()
                parser.setFeature(xml.sax.handler.feature_namespaces, 1)
                parser.setContentHandler(ClipExtractor(buffer, request.GET['id']))
                try:
                    parser.parse(file)
                except ClipExtractor.Done:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug('Parsing  of "%s.svg" stopped', image, exc_info=True) 
                return HttpResponse(buffer.getvalue(),
                                    content_type='image/svg+xml')
            else:
                fraction = request.GET.get('fraction', 1)
                fraction = int(fraction)
                if 0 >= fraction:
                    return HttpResponseNotFound()
                finder = ClipFinder(fraction)
                file = open(file, encoding = 'UTF-8')
                parser = xml.sax.make_parser()
                if not isinstance(parser, xml.sax.xmlreader.IncrementalParser):
                    log.info(
                        'Default SAX parser %s does not support incremental'
                        ' parsing', type(parser))
                    try:
                        parser.close()
                    except:
                        log.warning('Error closing SAX parser of %s',
                                    type(parser), exc_info = True)
                    from xml.parsers import expat
                    parser = expat.ParserCreate()
                parser.setContentHandler(finder)
                parser.setFeature(xml.sax.handler.feature_namespaces, 1)
                lineno = 0
                try:
                    for line in file:
                        lineno += 1
                        parser.feed(line)
                        if finder.done:
                            break
                    if finder.targetId:
                        return HttpResponsePermanentRedirect(
                            '?' + urlencode({'id': finder.targetId}))
                    else:
                        raise ValueError(
                           'Could not find image clip with supplied parameters'
                        )
                except xml.sax.SAXException as error:
                    if error._msg:
                        error._msg += ' '
                    error._msg += 'at line %d' % lineno
                    raise error                  
                finally:
                    parser.setErrorHandler(SAXErrorSuppressor())
                    parser.close()
        except:
            log.error('Error processing request for 1/%s-th of "%s.svg"',
                      fraction, image, exc_info=True)
            return HttpResponseServerError()
        finally:
            if hasattr(file, 'close'):
                file.close()

class ContentHandler(xml.sax.handler.ContentHandler):
        
    @classmethod
    def _distanceAttr(cls, attrs, attr):
        if isinstance(attr, collections.Sequence) and not isinstance(attr, str):
            value = attrs.get(attr)
        else:
            value = attrs.get((None, attr))
        if not value:
            return None
        stripped = value.strip()
        match = cls.PATTERN_NUMBER.match(stripped)
        if not match:
            raise ValueError('"%s" is not a valid SVG distance.' % value)
        unit = stripped[match.end():]
        try:
            value = float(match[0])
        except:
            raise ValueError(
                '%s = "%s"' % (attr, value))
        if not math.isfinite(value):
            raise ValueError(
                '%s = "%s"' % (attr, value))
        return value, unit

#     def _splitNS(self, name):
#         plen = name.rfind(':')
#         if 0 <= plen:
#             prefix = name[:plen]
#             name = name[plen + 1:]
#         else:
#             prefix = ''
#         ns = None
#         mappings = self._prefixes.get(prefix)
#         if mappings:
#             ns = mappings[-1]
#         elif prefix:
#             raise xml.sax.SAXParseException(
#                 'No namespace mapping found for XML element <%s:%s>'
#                 % (prefix, name), 
#                 None, 
#                 self._locator)
#         return ns, name

    @classmethod
    def parseBox(class_, attrValue):
        attrValue = attrValue.strip()
        box = class_.PATTERN_COORDINATE_DELIMITER.split(attrValue, 3)
        for i in range(len(box)):
            try:
                box[i] = float(box[i])
            except:
                raise ValueError('Invalid box coordinate "%s" at index %d'
                                 % (box[i], i)) from sys.exc_info()[1]
        return tuple(box)

    @staticmethod
    def boxValue(rect):
        # TODO: is this used?
        return ' '.join(("%.6f" % c for c in rect))


    PATTERN_NUMBER = re.compile(r'[+-]?(?:[0-9]*\.[0-9]+|[0-9]+)(?:[Ee][0-9]+)?')
    PATTERN_COORDINATE_DELIMITER = re.compile(r'\s*,\s*|\s+')

class ClipFinder(ContentHandler):

    done = False
    targetId = None

    def __init__(self, fraction):
        self.fraction = fraction

    def startDocument(self):
        self._context = []
        self._uses = []

    def endDocument(self):
        self._uses = None

    def setDocumentLocator(self, locator):
        self._locator = locator

    def startElementNS(self, name, qname, attrs):
        self._context.append(name)
        handler = self.ELEMENTS.get(name)
        if handler is not None:
            handler(self, attrs, *name)

    def endElementNS(self, name, qname):
        context = self._context.pop()
        assert name == context

    def elementUse(self, attrs, ns, name):
        id_ = attrs.get(CardBackView.XLINK_HREF_ATTR)
        if not (id_ and id_.startswith('#')):
            return
        width, unit = self._distanceAttr(attrs, 'width')
        if self._uses and unit != self._uses[-1][2]:
            raise xml.sax.SAXParseException(
                'Uniform units expected in preamble`s <use>'
                ' elements, got "%s" and "%s"' %
                (self._uses[-1][3], unit),
                None,
                self._locator
            ) 
        if width is not None:
            self._uses.append((width, id_[1:], unit))

    def elementDefs(self, attrs, ns, name):
        if self._uses:
            self._uses.sort(key=lambda u: u[0], reverse=True)
            last = self._uses[0]
            width = last[0] / self.fraction
            for use in self._uses[1:]:
                if width > use[0]:
                    break
                last = use
            self.targetId = last[1]
        self.done = True

    ELEMENTS = {
        (CardBackView.SVG_NAMESPACE, 'use'): elementUse,
        (CardBackView.SVG_NAMESPACE, 'defs'): elementDefs,
    }

class ClipExtractor(ContentHandler):
    
    def __init__(self, output, clipId):
        self._sink = XMLGenerator(output, 'UTF-8', True)
        self._locator = None
        self._id = clipId

    def setDocumentLocator(self, locator):
        self._locator = locator
        self._skip = None
        self._stopAt = None 
        return self._sink.setDocumentLocator(locator)

    def startDocument(self):
#         self._prefixes = {}
        self.scale = self.units = None
        self._context = []
        self._outerSvgRendered = False
        return self._sink.startDocument()

    def endDocument(self):
#         self._prefixes.clear()
        return self._sink.endDocument()

    def startPrefixMapping(self, prefix, uri):
        self._context.append(('xmlns', None, prefix, uri))
#         mappings = self._prefixes.get(prefix)
#         if mappings is None:
#             self._prefixes[prefix] = mappings = []
#         mappings.append(uri)
        return self._sink.startPrefixMapping(prefix, uri)
  
    def endPrefixMapping(self, prefix):
        context = self._context.pop()
        assert ('xmlns', None, prefix) == context[:-1]
#         mappings = self._prefixes.get(prefix)
#         assert mappings is not None
#         mappings.pop()
        return self._sink.endPrefixMapping(prefix)

    def startElement(self, qname, attrs):
        raise xml.sax.SAXNotSupportedException(
                'This handler must be used with feature "%s"'
                ' turned on'
                % xml.sax.handler.feature_namespaces 
            )
#         if 'xmlns' in attrs:
#             if self._context:
#                 raise xml.sax.SAXNotSupportedException(
#                     'This document must be parsed with feature "%s"'
#                     ' turned on'
#                     % xml.sax.handler.feature_namespaces 
#                 )
#             else:
#                 self.startPrefixMapping('', attrs.get('xmlns'))
#         ns, name = self._splitNS(qname)
#         handler = self.ELEMENTS.get((ns, name))
#         if handler and handler[0]:
#             update = handler[0](self, attrs, ns, name)
#             if not update:
#                 if self._skip is None:
#                     self._skip = len(self._context) + 1
#             elif isinstance(update, collections.Sequence):
#                 attrs = update[0]
#                 if len(update) > 1:
#                     ns, name, qname = update[1:]
#         self._context.append((ns, name, qname, attrs.copy()))
#         if self._skip is None:
#             return self._sink.startElement(qname, attrs)

    def endElement(self, qname):
        raise xml.sax.SAXNotSupportedException(
                'This handler must be used with feature "%s"'
                ' turned on'
                % xml.sax.handler.feature_namespaces 
            )
#         ns, name = self._splitNS(qname)
#         handler = self.ELEMENTS.get((ns, name))
#         if handler and handler[1]:
#             handler[1](self, ns, name)
#         context = self._context.pop()
#         assert (ns, name) == context[:2]
#         if self._skip is None:
#             self._sink.endElement(qname)
#         elif len(self._context) < self._skip:
#             self._skip = None
#         if len(self._context) == self._stopAt:
#             raise self.Done('extraction complete',
#                             self._locator.getLineNumber(),
#                             self._locator.getColumnNumber()
#                         ) 

    def startElementNS(self, name, qname, attrs):
        if (None, 'xmlns') in attrs:
            self.startPrefixMapping(None, attrs.get('xmlns'))
        handler = self.ELEMENTS.get(name)
        if handler and handler[0]:
            update = handler[0](self, attrs, *name, qname)
            if not update:
                if self._skip is None:
                    self._skip = len(self._context) + 1
            elif isinstance(update, collections.Sequence):
                attrs = update[0]
                if len(update) > 1:
                    name  = tuple(update[1:3])
                if len(update) > 3:
                    qname = update[3]
        self._context.append(name + (qname, attrs.copy()))
        if self._skip is None:
            return self._sink.startElementNS(name, qname, attrs)

    def endElementNS(self, name, qname):
        handler = self.ELEMENTS.get(name)
        if handler and handler[1]:
            handler[1](self, *name, qname)
        context = self._context.pop()
        assert name == context[:2]
        if self._skip is None:
            self._sink.endElementNS(name, qname)
        elif len(self._context) < self._skip:
            self._skip = None
        if len(self._context) == self._stopAt:
            while self._context:
                toClose = self._context.pop()
                if 'xmlns' == toClose[0]:
                    self._sink.endPrefixMapping(toClose[2])
                else:
                    self._sink.ignorableWhitespace('\n')            
                    self._sink.endElementNS(toClose[:2], toClose[2])
            self._sink.endDocument()
            raise self.Done('extraction complete',
                            ( self._locator.getLineNumber(),
                            self._locator.getColumnNumber() )
                        ) 

    def elementSvgEnd(self, *args):
        attrs = self._context[-1][3]
        if self.ATTR_ID in attrs and \
                self._id == attrs.get(self.ATTR_ID):
            self._stopAt = len(self._context) - 1

    def elementSvgStart(self, attrs, *args):
        if any( (CardBackView.SVG_NAMESPACE, 'svg') == e[:2]
                for e in self._context ):
            return self.ATTR_ID in attrs and \
                self._id == attrs.get(self.ATTR_ID)
        elif not 'viewBox' in attrs and not (None, 'viewBox') in attrs:
                self._error(None,
                    'Main <svg> element has no viewBox attribute')
        else:
            try:
                internalSize = attrs.get((None, 'viewBox'))
                if internalSize is None:
                    internalSize = attrs.get('viewBox')
                internalSize = self.parseBox(internalSize)[2:]
                externalSize = list(internalSize)
                units = [''] * 2
                i = -1
                for attr in CardBackView.ATTRS_SVG_DIMENSION:
                    i += 1
                    value, unit = self._distanceAttr(attrs, attr)
                    if unit.strip() == '%':
                        value = None
                    if value is not None: 
                        externalSize[i] = value
                        units[i] = unit
                self.units = tuple(units)
                try:
                    self.scale = tuple(
                        e/i for e,i in zip(externalSize, internalSize)
                    )
                except ZeroDivisionError as error:
                    self._error(None,
                        'Found <svg> with zero dimension(s), viewBox="%s"'
                        % attrs.get((None, 'viewBox')))
                return False
            except:
                self._error()

    def elementUseStart(self, attrs, ns, name, qname):
        target = attrs.get(CardBackView.XLINK_HREF_ATTR)
        if not target:
            return False
        target = target.strip()
        if '#' == target[0] and self._id == target[1:] \
             and not self._outerSvgRendered:
            try:
                outerSvg = next( e for e in self._context
                             if (CardBackView.SVG_NAMESPACE, 'svg') == e[:2] )
            except StopIteration:
                self._error(None, 'Found <use> element outside of an <svg>')
            size = []
            for attr in CardBackView.ATTRS_SVG_DIMENSION:
                value, unit = self._distanceAttr(attrs, attr)
                if unit.strip():
                    self._error(None,
                                'Attribute <use %s="%s" ...> is not valid'
                                ' in this context, expected a unit-free number.'
                                % (attr, attrs.get(None, attr)))
                if value is None: 
                    self._error(None,
                                'Attribute `%s` is missing from <use> element,'
                                ' but is expected in this context.'
                                % attr)
                size.append(value)
            sattrs = ( '%.6f%s' % (s*v, u) for s,v,u in
                       zip(self.scale, size, self.units) )
            qnames = { name: outerSvg[3].getQNameByName(name)
                      for name in outerSvg[3].getNames() }
            attrMap = dict(outerSvg[3].items())
            attrMap[(None, 'viewBox')] = self.boxValue((0, 0) + tuple(size))
            for attr in zip(CardBackView.ATTRS_SVG_DIMENSION, sattrs):
                attrMap[(None, attr[0])] = attr[1] 
            self._sink.startElementNS(
                outerSvg[:2],
                outerSvg[2], 
                AttributesNSImpl(attrMap, qnames)
            )
            self._sink.ignorableWhitespace('\n')
            self._outerSvgRendered = True
            qnames = { name: attrs.getQNameByName(name)
                      for name in attrs.getNames() }
            attrMap = dict(attrs.items())
            for attr in ('x', 'y') + CardBackView.ATTRS_SVG_DIMENSION:
                qnames.pop((None, attr), None)
                attrMap.pop((None, attr), None)
            self._sink.startElementNS((ns, name), qname, 
                AttributesNSImpl(attrMap, qnames))
            self._sink.endElementNS((ns, name), qname)
            self._sink.ignorableWhitespace('\n')            
        return False

    def elementDefsStart(self, attrs, *args):
        if not self._outerSvgRendered:
            self._error(None,
                        'Element <use xlink:href="#%s" ...> must precede'
                        ' the <defs> element in this context.'
                        % self._id)
        self._skip = None
        return True

    ATTR_ID = (None, 'id')

    ELEMENTS = {
        (CardBackView.SVG_NAMESPACE, 'svg'): (elementSvgStart, elementSvgEnd),
        (CardBackView.SVG_NAMESPACE, 'use'): (elementUseStart, None),
        (CardBackView.SVG_NAMESPACE, 'defs'): (elementDefsStart, None),
    }

    def characters(self, content):
        if self._skip is None:
            return self._sink.characters(content)

    def ignorableWhitespace(self, whitespace):
        if self._skip is None:
            return self._sink.ignorableWhitespace(whitespace)

    def processingInstruction(self, target, data):
        if self._skip is None:
            return self._sink.processingInstruction(target, data)

    def skippedEntity(self, name):
        if self._skip is None:
            return self._sink.skippedEntity(name)

    def _error(self, error = True, message = ''):
        if error == True:
            error = sys.exc_info()[1]
        if error is None:
            assert message
            error = SAXParseException(message, None,
                    self._locator)
        elif not isinstance(error, SAXParseException):
            msg = error.args[0] if error.args else ''
            if msg:
                msg += ' '
            if message:
                msg += message + ' '
            error.args = (msg + 'at line %d, column %d.' % (
                    self._locator.getLineNumber(),
                    self._locator.getColumnNumber()
                ),) + error.args[1:] 
        raise error

    class Done(xml.sax.SAXException):
        pass
    
#     PATTERN_IMAGE_ID = re.compile(r'(?:clip|image)-([\d.]+)x([\d.]+)')

class SAXErrorSuppressor(xml.sax.handler.ErrorHandler):
    def error(self, exception):
        pass
    def fatalError(self, exception):
        pass
    def warning(self, exception):
        pass
