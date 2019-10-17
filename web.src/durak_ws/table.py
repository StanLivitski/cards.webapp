# vim:fileencoding=UTF-8 
#
# Copyright © 2016, 2017, 2019 Stan Livitski
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
import json
import logging

import django.urls
from django.http.response import \
    HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError,\
    HttpResponseNotFound, HttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from comety.django.views import ViewWithEvents

from .models import PlayerCheckIn
from .intro import IntroView

class TableView(ViewWithEvents):
    """
    TODO
    """

    http_method_names = ['get', 'post']
    TABLE_LAYOUTS = { '4x3', '9x16' }
    SEATING_CAPACITY = 8
    STATUS_ICONS = {
        'attacking': ('glyphicon-hand-left', _('attacks'), _('you attack')),
        'defending': ('glyphicon-screenshot', _('defends'), _('you defend')),
        'collecting': ('glyphicon-remove-sign', _('collects'), _('you collect')),
        'quit': ('glyphicon-ok-sign', _('quits'), _('you quit')),
        'other': None
    }

    GAME_IN_SESSION = IntroView.GAME_IN_SESSION
    PLAYER_IN_SESSION = IntroView.PLAYER_IN_SESSION

    updateMode = False

    def post(self, request, *args, **kwargs):
        if not self._isRequestAdmitted(request):
            return HttpResponseRedirect(
                django.urls.reverse('intro')
            )
        elif self.updateMode:
            return HttpResponse('OK') if self._admittedPost(request) \
                else HttpResponseServerError('REJECTED')
        else:
            self._admittedPost(request)
            return self._admittedGet(request)

    def get(self, request, *args, **kwargs):
        if not self._isRequestAdmitted(request):
            return (HttpResponseForbidden() if self.updateMode
                else HttpResponseRedirect(
                    django.urls.reverse('intro')
                ))
        elif self.updateMode:
            response = super().get(request, *args, **kwargs)
            if self.checkIn.game and not self.checkIn.game.playing:
                request.session[IntroView.SHOW_RESULT_IN_SESSION] = True
            return response
        else:
            return self._admittedGet(request)

    def _isRequestAdmitted(self, request):
        """
        Determines whether this session belongs to an admitted player and
        resets the user's heartbeat timer if applicable.

        Parameters
        ----------
        request : django.http.HttpRequest
            The web request being processed.

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
        if passed and not self.updateMode:
            passed = checkIn.game and checkIn.game.playing
        if passed:
            self.checkIn = checkIn
            self.heartbeat(playerId)
        return passed

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
            checkIn = self.checkIn
            position = checkIn.tokens[userId]
            player = checkIn.game.players[position]
            action = request.POST['action']
            args = request.POST.get('args', False)
            args = json.loads(args if args else 'null')
            player.attemptMove(action, args)
            return True
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error processing action by user "%s"',
                      userId, exc_info=True)
            return False

    def _admittedGet(self, request):
        """
        Process a ``GET`` request from an admitted player.

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
        checkIn = self.checkIn
        try:
            ui = checkIn.getUiDispatcher()
            ui.confirmEvents(userId)
            layout = request.GET.get('layout')
            if layout is not None and layout not in self.TABLE_LAYOUTS:
                return HttpResponseNotFound(
                    ugettext('Unknown table layout: "%s"') % layout,
                    content_type='text/plain; charset=utf-8'
                )
            position = checkIn.tokens[userId]
            opponents = checkIn.opponentMap(position, self.SEATING_CAPACITY)
            contextVars = {
                'bodyClass' : "table-background",
                'backImage' : '01',
                'game' : checkIn.game,
                'gameApp' : 'durak',
                'layoutTemplate' : 'durak/table/%s.html' % layout,
                'opponents' : opponents,
                'player' : checkIn.game.players[position],
                'position' : position,
                'statum' : self.STATUS_ICONS,
                'tableLayout' : layout,
            }
            response = render(request, 'durak/table.html', contextVars)
            self.clearDelayStats(request.session)
            self.trackHeartbeat(request, True)
            return response
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error serving %s to user "%s"', type(self).__name__,
                      userId, exc_info=True)
            return HttpResponseServerError()

    def cometyDispatcherFor(self, request, *args, **kwargs): # TODO: share with the intro view
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
        return (checkIn.getUiDispatcher()
                if checkIn is not None 
                else None)

    def identifyUser(self, request, *args, **kwargs): # TODO: share with the intro view
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

    def disconnectSession(self, token): # TODO: share with the intro view
        """
        Invalidate an inactive session to allow a player to
        reconnect. 
        
        This method should be called when the application
        detects that a player has disconnected. It delegates
        to `sessionByUser` in superclass to retrieve
        that player's session by her token, and invalidates
        the session by removing the variable with
        `GAME_IN_SESSION` key.
        
        Parameters
        ----------
        token : str
            Token of the player that is no longer connected.
    
        Raises
        ------
        TypeError
            If ``token`` is not a string.
        KeyError
            If there is no mapping for ``token`` to session key
            in the cache.
    
        See Also
        --------    
        sessionByUser : A base class' method to retrieve the session
        object for a specific user.
        GAME_IN_SESSION : TODOdoc
    
    [   Examples
        --------
        <In the doctest format, illustrate how to use this method.>
         ]
        """

        session = self.sessionByUser(token)
        del session[self.GAME_IN_SESSION]
        session.save()
