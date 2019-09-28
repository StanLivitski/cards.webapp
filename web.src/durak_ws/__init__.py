# vim:fileencoding=UTF-8 
#
# Copyright © 2015, 2016, 2017 Stan Livitski
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
A service that connects the `cards.durak` model to web application
front-ends.

This module contains the application-wide configuration. 
"""
import importlib
import logging
import os.path

from django.apps.registry import apps
from django.apps.config import AppConfig
from django.utils.cache import patch_response_headers

def cache_streaming_page(max_age):
    def wrap(view):
        nonlocal max_age
        def wrapper(*args, **kwargs):
            nonlocal view, max_age
            response = view(*args, **kwargs)
            patch_response_headers(response, max_age) 
            return response
        return wrapper
    return wrap

class Application(AppConfig):
    """
    Django application configuration class.
    
    <Extended description>
    
[    Attributes
    -----------------
    <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
    ready()
        Registers the application's signals.
[
    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

[    See Also
    --------------
    <python_name> : <Description of code referred by this line
    and how it is related to the documented code.>
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

    name = locals()['__module__']   # PyDev complains if __module__ is referenced directly  

    def ready(self):
        """
        Initialize this application.
        
        Registers the application's signals and configures the 
        ``staticfiles`` app to enable client-side caching.
        
    [    Raises
        ------
        <exception_type>
            <Description of an error that may get raised and under what conditions.
            List only errors that are non-obvious or have a large chance of getting raised.>
        ... ]
    
    [    See Also
        --------    
        <python_name> : <Description of code referred by this line
        and how it is related to the documented c#ode.>
         ... ]
        """
        
        super().ready()
        from . import signals, graphics
        static_app = None
        try:
            static_app = apps.get_app_config('staticfiles')
            static_views = importlib.import_module('.views',
                                     static_app.module.__name__)
            if static_views.serve is not graphics.disable_session:
                static_views.serve = graphics.disable_session(
                    cache_streaming_page(graphics.SVGView.AGE_GRAPHICS_CACHE)
                    (static_views.serve))
        except:
            log = logging.getLogger(type(self).__module__)
            log.warning('Could not annotate function .views.serve of %s',
                        'the `staticfiles` app' if static_app is None
                        else static_app.module, exc_info = True)
