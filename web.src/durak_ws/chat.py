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
import logging
import math

from django.http.response import \
    JsonResponse, HttpResponse, \
    HttpResponseForbidden, HttpResponseServerError # HttpResponseNotFound
from django.shortcuts import render
from django.utils.translation import ugettext as _

from comety import FilterByTargetUser
from comety.django.views import ViewWithEvents, JSONEncoder

from durak_ws.models import PlayerCheckIn
from .intro import IntroView
import comety
import collections

"""
    <Short summary>
    
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

class ChatView(ViewWithEvents):
    """
    <Short summary>
    
    <Extended description>
    
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

[    Other parameters
    ------------------------------
    <var>[, <var>] : <type | value-list>[, optional]
        <Description of infrequently used constructor's parameter(s)>
    ... ]

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errors that are non-obvious or have a large chance of getting raised.>
    ... ]

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

    GAME_IN_SESSION = IntroView.GAME_IN_SESSION
    PLAYER_IN_SESSION = IntroView.PLAYER_IN_SESSION

    MESSAGE_EVENT = 'message'

#    def __init__(self, params):
#        pass    # TODO: implement

    updateMode = False
    http_method_names = ['get', 'post']

    def _externalizeUserInfo(self, userId):
        checkIn = PlayerCheckIn.FACILITIES[userId]
        player = checkIn.fetchPlayer(token = userId)
        return player.name, checkIn.tokens[userId]

    def _admittedPost(self, request):
        """
        Process a ``POST`` request from an admitted player.

        Parameters
        ----------
        request : django.http.HttpRequest
            The web request being processed.

        Returns
        -------
        boolean
            Success status of processing. 
        """

        userId = request.session[self.PLAYER_IN_SESSION]
        try:
            checkIn = PlayerCheckIn.FACILITIES[userId]
            text = request.POST['text']
            if (8000 < len(text)):
                raise ValueError('Message text is too long: 8000 < %d', len(text))
            targetUser = request.POST.get('to')
            targetUser = checkIn.getId(int(targetUser)) if targetUser else None
            self.cometyDispatcher.postEvent(self._externalizeUserInfo(userId),
                           event = self.MESSAGE_EVENT,
                           text=text, targetUsers=targetUser)
            return True
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error processing action by user "%s"',
                      userId, exc_info=True)
            return False

    def _admittedUpdate(self, request):
        """
        Process a Comety update request from an admitted player.

        Parameters
        ----------
        request : django.http.HttpRequest
            The web request being processed.

        Returns
        -------
        django.http.HttpResponse
            The application's response. 
        """

        userId = request.session[self.PLAYER_IN_SESSION]
        try:
            chat = self.cometyDispatcher
            expectedDelay = self.expectedDelay(request.session)
            maximumTimeout = float(request.GET['timeout'])
            if maximumTimeout is None:
                timeout = self.HEARTBEAT_TIMEOUT * self.RESPONSE_TIMEOUT_FACTOR - expectedDelay
            elif 0 > maximumTimeout or not math.isfinite(maximumTimeout):
                raise ValueError(
                   '"maximumTimeout" must be a finite positive number or zero, got %g'
                   % maximumTimeout
                )
            else:
                timeout = maximumTimeout * self.RESPONSE_TIMEOUT_FACTOR - expectedDelay
            if 0 > timeout: timeout = 0
            confirm = request.GET.get('confirm')
            if confirm is not None:
                confirm = int(confirm)
                if 0 > confirm:
                    raise ValueError(
                       '"confirm" is negative: %d' % confirm)
                else:
                    chat.confirmEvents(userId, confirm)
            filter_ = FilterByTargetUser(userId)
            events = chat.pollEvents(userId, timeout, filter_, True)
            if events[1]:
                eventList = []
                for event in events[1]:
                    targetUsers = event.arg('targetUsers')
                    if targetUsers is not None:
                        kwargs = dict(event.kwargs)
                        if isinstance(targetUsers, str):
                            targetUsers = self._externalizeUserInfo(targetUsers)
                        elif isinstance(targetUsers, collections.Iterable):
                            raise NotImplementedError('Cannot send message to multiple users') 
                        else:
                            raise ValueError('Unknown target user object %s' % type(targetUsers))                             
                        kwargs['targetUsers'] = [ targetUsers ]
                        event = comety.Dispatcher.Event(event.sender, **kwargs)
                    eventList.append(event)
                events = (events[0], eventList)
            return JsonResponse(
                {
                    'lastId': events[0],
                    'events': events[1] if events[1] else None  
                },
                encoder=JSONEncoder
            )
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error serving %s to user "%s"', type(self).__name__,
                      userId, exc_info=True)
            return HttpResponseServerError()

    def _isRequestAdmitted(self, request, *args):
        """
        Determines whether this session belongs to an admitted player and
        resets the user's heartbeat timer if applicable.

        Request with positional arguments is assumed to be a join request
        and is never considered admitted.

        Parameters
        ----------
        request : django.http.HttpRequest
            The web request being processed.
        args : collections.Sequence
            Positional arguments parsed from the request.

        Returns
        -------
        bool
            The answer whether this session belongs to an admitted player.

        See Also
        --------
        heartbeat :
            Method used to stop any existing heartbeat timer for the user.
        """

        gameId = request.session.get(self.GAME_IN_SESSION)
        checkIn = None if gameId is None else PlayerCheckIn.FACILITIES.get(gameId)
        playerId = request.session.get(self.PLAYER_IN_SESSION)
        passed = (
            checkIn is not None and
            checkIn.id == gameId and
            playerId is not None and
            playerId in checkIn.tokens
        )
        if passed:
            self.heartbeat(playerId)
        return passed

    def cometyDispatcherFor(self, request, *args, **kwargs):
        """
        Locate the Comety dispatcher for a request by querying
        active `PlayerCheckIn` model.
        
        Parameters
        ----------
        request : django.http.request.HttpRequest
            HTTP request served by this view.
        *args : list
            Optional positional arguments passed to the view.
        ***kwargs : dict
            Optional keyword arguments passed to the view.
    
        Returns
        -------
        Dispatcher
            Comety dispatcher that will service this request.
        """

        id_ = request.session.get(self.PLAYER_IN_SESSION)
        checkIn = None if id_ is None else PlayerCheckIn.FACILITIES.get(id_)
        return (checkIn.chatDispatcher
                if checkIn is not None 
                else None)

    def identifyUser(self, request, *args, **kwargs):
        """
        Determine user's identity from the session.
        
        Parameters
        ----------
        request : django.http.request.HttpRequest
            HTTP request served by this view.
        *args : list
            Optional positional arguments passed to the view.
        ***kwargs : dict
            Optional keyword arguments passed to the view.
    
        Returns
        -------
        collections.Hashable | NoneType
            Identity of the user that sent the request or
            ``None`` if no valid user is associated with this
            session.
        """

        id_ = request.session.get(self.PLAYER_IN_SESSION)
        checkIn = None if id_ is None else PlayerCheckIn.FACILITIES.get(id_)
        gameId = request.session.get(self.GAME_IN_SESSION)
        return (id_ if checkIn is not None and gameId == checkIn.id else None)           

    def get(self, request, *args, **kwargs):
        if not self._isRequestAdmitted(request, *args):
            return HttpResponseForbidden()
        elif self.updateMode:
            return self._admittedUpdate(request)
        else:
            userId = request.session[self.PLAYER_IN_SESSION]
            checkIn = PlayerCheckIn.FACILITIES[userId]
            seat = checkIn.tokens[userId]
            return render(request, 'chat.html', {
                'seat' : seat
            })

    def post(self, request, *args, **kwargs):
        if not self._isRequestAdmitted(request):
            return HttpResponseForbidden()
        elif self.updateMode:
            return HttpResponse('OK') if self._admittedPost(request) \
                else HttpResponseServerError('REJECTED')
        else:
            self._admittedPost(request)
            log = logging.getLogger(type(self).__module__)
            log.warning(
                'Chat window of user "%s" submitted a POST request. This is'
                + ' test-only feature that may be dropped in future.',
                  request.session.get(self.PLAYER_IN_SESSION))
            return self.get(request, *args, **kwargs)
