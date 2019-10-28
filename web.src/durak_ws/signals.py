# vim:fileencoding=UTF-8 
#
# Copyright © 2016 Stan Livitski
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
durak_ws application-wide signal handlers.

<Extended description>

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
    -----
    <Additional information about the code, possibly including
    discussion of the algorithms. Follow it with a 'References'
    section if citing any references.>
]

[    Examples
    --------
    <In the doctest format, illustrate how to use this module.>
]
"""

from django.dispatch import receiver
from comety.django.views import ViewWithEvents

@receiver(ViewWithEvents.USER_TIMEOUT_SIGNAL)
def expireSession(sender, **kwargs):
    """
    Receive a session expiration signal and dispatch it
    to the appropriate model based on the arguments.
    
    This callback receives `ViewWithEvents.USER_TIMEOUT_SIGNAL`
    signals, locates the appropriate model for the sending view,
    and dispatches the signal to the target model. 
    
    Parameters
    ----------
    sender : type
        The class of an object that send this event (usually,
        a view).
    
    Returns
    -------
    bool
        Explicitly returns ``False`` to enable the sender to
        de-register the expired user.

    Other parameters
    ----------
    cometyDispatcher : comety.Dispatcher
        Comety dispatcher that encountered the timeout.
        Use this reference to identify the scope of `userId`
        belonging to the expired session's user.
    userId : collections.Hashable
        Identity of the user that had her session expired.

    Raises
    ------
    NotImplementedError
        If ``sender`` is of an unknown type, which prevents this
        method from dispatching the signal correctly.

    See Also
    --------    
    ViewWithEvents.USER_TIMEOUT_SIGNAL : The signal received by
    this callback.
    """

    from . import models # TODO: additional views, if any
    if isinstance(type(sender), type) and issubclass(sender, ViewWithEvents):
        userId = kwargs['userId']
        view = sender()
        if isinstance(view, ViewWithEvents):
            session = view.sessionByUser(userId)
            view.disconnectSession(session)
        checkIn = models.PlayerCheckIn.FACILITIES.get(userId)
        if checkIn is not None:
            checkIn.playerConnectionStatus(userId)
    else:
        # NOTE: game id is required to disconnect a player from the game view
        raise NotImplementedError(
            'Received user timeout from an unknown source: %s'
            % sender
        )