# vim:fileencoding=UTF-8 
#
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
    Django templates for manipulating data collections.
    
    TODO: Extended description

    Key elements
    ------------
    <python_name> : <One-line summary of a class, exception,
    function, or any other object exported by the module and
    named on this line.>
    <The docstring for a package's ``__init__`` module should,
    in most cases list the modules and subpackages exported by
    the package here. >
    ...

"""

from django import template
import collections

register = template.Library()

@register.filter
def get(collection, indexOrKey):
    """
    Retrieve an item from a collection.
    
    TODO: Extended description
    
    Parameters
    --------------------
    collection : Sequence | Mapping
        The collection to look up.
    indexOrKey : object
        The key or index of an item.

    Returns
    ------------------------------
    object
        the requested item, or ``None`` if it dosen't exist

    Raises
    ----------
    TypeError
        If `collection` does not support element lookups,
        or `indexOrKey` is of an inappropriate type for the
        `collection`.

    Examples
    ----------------
    TODO: <In the doctest format, illustrate how to use this filter.>
    """

    if isinstance(collection, collections.Mapping):
        return collection.get(indexOrKey)
    elif '__getitem__' in dir(collection):
        try:
            return collection.__getitem__(indexOrKey)
        except LookupError:
            return None
    else:
        raise TypeError(
            'Object of %s does not support element lookups'
            % type(collection)
        )
