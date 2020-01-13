# vim:fileencoding=UTF-8 
#
# Copyright © 2015 - 2020 Stan Livitski
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
import collections
import importlib
import logging
import socket
import sys
from urllib.parse import urlunsplit

import django.urls
from django.conf import settings
from django.http.response import \
    HttpResponse, HttpResponseForbidden, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.utils.translation import ugettext as _

import callables
import mapping
from comety.django.views import ViewWithEvents

import durak_ws
from cards_web.connect import InboundAddressEnumerator, \
    Authenticator, local_client_authenticator
from durak_ws.models import PlayerCheckIn, RemoteEntity, WebGame
from builtins import issubclass

class IntroView(ViewWithEvents):
    """
    Renders a page that allows an authenticated user to create
    a game and other players to join it over the web and provides
    asynchronous updates to users of that page.

    Methods
    -------
    getPAM()
        Returns an authenticator from the PAM configured for this
        application.
    """

    http_method_names = ['get', 'post']

    GAME_IN_SESSION = durak_ws.__name__ + '_game_id'
    PLAYER_IN_SESSION = durak_ws.__name__ + '_player_id'
    ERROR_IN_SESSION = durak_ws.__name__ + '_error'
    SHOW_RESULT_IN_SESSION = durak_ws.__name__ + '_show_result'

    updateMode = False

    def player_name_set(self, name, request):
        """
        Receives updates to ``player-name`` field.


        Parameters
        ----------
        name : str
            The new name of a player that owns the current session.
        request : django.http.HttpRequest
            HTTP request that caused this change.
       
        Raises
        ------
        Exception
            If the model will not accept this update, for example due to
            invalid argument values. 
        """

        token = request.session[IntroView.PLAYER_IN_SESSION]
        self.checkIn.updatePlayer(token, name = name)

    def settings_players_set(self, setting, request):
        """
        Receives updates to ``settings-players`` field. 
        
        
        Parameters
        ----------
        setting : collections.Sequence | str
            The new number of players represented as decimal string.
            A `collections.Sequence` may also be passed here, but will
            result in exception.
        request : django.http.HttpRequest
            HTTP request that caused this change.
       
        Raises
        ------
        Exception
            If the model will not accept this update, for example due to
            invalid argument values. 
        """

        self.checkIn.capacity = int(setting)


    def settings_lowestCardRank_set(self, setting, request):
        """
        Receives updates to ``settings-lowestCardRank`` field. 
        
        
        Parameters
        ----------
        setting : collections.Sequence | str
            The new low card rank limit represented as decimal string.
            A `collections.Sequence` may also be passed here, but will
            result in exception.
        request : django.http.HttpRequest
            HTTP request that caused this change.
       
        Raises
        ------
        Exception
            If the model will not accept this update, for example due to
            invalid argument values. 
        """

        self.checkIn.lowestCardRank = int(setting)

    def settings_connectToAddress_set(self, setting, request):
        """
        Receives updates to ``settings-connectToAddress`` and
        ``settings-connectToOther`` fields. 
        
        
        Parameters
        ----------
        setting : collections.Sequence | str
            The new index into the `InboundAddressEnumerator.FACILITY`
            sequence, a string with prefix ``:`` followed by externally
            visible name or address, or an empty string if such name or
            address is passed via the ``settings-connectToOther`` field.
            A `collections.Sequence` may also be passed here, but will
            result in exception.
        request : django.http.HttpRequest
            HTTP request that caused this change to extract the
            ``settings-connectToOther`` value if necessary.
       
        Raises
        ------
        Exception
            If the model will not accept this update, for example due to
            invalid argument values. 
        """

        if type(setting) is not str:
            raise TypeError(
                'Unexpected `settings-connectToAddress` value of %s'
                % type(setting)
            )
        elif setting.isdigit():
            self.checkIn.host = int(setting)
            self.checkIn.port = None
        elif setting.startswith(':'):
            self.checkIn.host = setting[1:]
            self.checkIn.port = None
        elif not setting:
            hostport = request.POST['settings-connectToOther']
            if type(hostport) is not str:
                raise TypeError(
                    'Unexpected `settings-connectToOther` value of %s'
                    % type(hostport)
                )
            hostport = hostport.strip()
            port = None
            at = len(hostport)
            while 0 < at:
                at -= 1
                if not hostport[at].isdigit():
                    break
            if hostport and 0 <= at and ':' == hostport[at]:
                host = hostport[:at]
                if len(hostport) > at + 1:
                    port = int(hostport[at + 1:]) 
            else:
                host = hostport
            if not host:
                raise ValueError(
                    'Invalid `settings-connectToOther` value: %s'
                    % repr(hostport)
                )
            self.checkIn.host = host
            self.checkIn.port = port
        else:
            raise ValueError(
                'Unexpected `settings-connectToAddress` value: %s'
                % repr(setting)
            )

    SETTINGS_HANDLERS = mapping.ImmutableMap({
        'players' : settings_players_set,
        'connectToAddress' : settings_connectToAddress_set,
        'lowCardRank' : settings_lowestCardRank_set,
    })

    @staticmethod
    def action_download_invitation(request):
        """
        Serve a page with invitation URL as an HTML download.
        """

        userId = request.session[IntroView.PLAYER_IN_SESSION]
        checkIn = PlayerCheckIn.FACILITIES[userId]
        try:
            # TODO: set `defaultPort` to None when it equals standard port for the protocol
            defaultPort = request.META['SERVER_PORT']
            seat = int(request.GET['seat'])
            if 0 == seat or 0 != checkIn.tokens[userId]:
                log = logging.getLogger(IntroView.__module__)
                log.error('Unauthorized invitation page request from'
                          + ' user id "%s" for seat %d',
                          userId, seat)
                return HttpResponseForbidden()
            contextVars = {
                'URLPrefix' : IntroView.getURLPrefix(request, checkIn, defaultPort),
                'token' : checkIn.getId(seat)
            }
            response = render(request, 'durak/invitation.html', contextVars)
            response['Content-Disposition'] = (
             'attachment; filename="player%d.html"' % (seat + 1))
            return response
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error serving invitation page for seat "%d"',
                      request.GET.get('seat'), exc_info=True)
            return HttpResponseServerError()

    @staticmethod
    def action_start(request):
        """
        Initiate a page switch in response to the "Start game" request.
        """

        target = None
        gameId = request.session.get(IntroView.GAME_IN_SESSION)
        checkIn = None if gameId is None else PlayerCheckIn.FACILITIES.get(gameId)
        try:
            checkIn.close()
            target = django.urls.reverse('table')
        except:
            error = sys.exc_info()[1]
            request.session[IntroView.ERROR_IN_SESSION] = \
             error.args[0] if error and error.args else type(error).__name__
        return None if target is None else HttpResponseRedirect(target)

    @staticmethod
    def action_hide_banner(request):
        """
        Modify session to prevent further game result banner shows.
        """

        request.session[IntroView.SHOW_RESULT_IN_SESSION] = False

    ACTIONS_HANDLERS = mapping.ImmutableMap({
        'banner-hide': action_hide_banner,
        'game-start' : action_start,
        'invitation-download' : action_download_invitation,
    })

    def _handleAction(self, action, request):
        """
        Look up and invoke a handler to fulfill an action request.


        Parameters
        ----------
        action : str | NoneType
            A key to the `ACTIONS_HANDLERS` map that will be
            used to look up a handler for this action.
        request : django.http.HttpRequest
            The web request being processed.
    
        Returns
        -------
        NoneType | django.http.response.HttpResponse
            HTTP response prepared by the handler, or ``None``
            if this view should respond via `_admittedGet`.
        """

        handler = self.ACTIONS_HANDLERS.get(action)
        if handler is not None:
            try:
                return callables.call(handler, globals(), self, request)
            except:
                log = logging.getLogger(type(self).__module__)
                log.error('Error processing action "%s"',
                          action, exc_info=True)

    def post(self, request, *args, **kwargs):
        if self._isRequestAdmitted(request, *args):
            # TODO: refactor me into `_admittedPost` method that changes settings
            prefix = 'settings-' 
            for param in request.POST:
                handler = None
                if param.startswith(prefix): 
                    setting = request.POST.getlist(param)
                    if 1 == len(setting): 
                        setting = setting[0]
                    handler = self.SETTINGS_HANDLERS.get(param[len(prefix):])
                elif param == 'player-name':
                    setting = request.POST[param]
                    handler = self.player_name_set
                if handler is not None:
                    try:
                        callables.call(handler, globals(), self, setting, request)
                    except:
                        log = logging.getLogger(type(self).__module__)
                        log.error('Error processing POST parameter "%s" = "%s"',
                                  param, setting, exc_info=True)
            action = request.POST.get('action')
            response = self._handleAction(action, request)
        else:
            response = self._admitRequest(request, *args, **kwargs)
        if response is None:
            if self.updateMode:
                return HttpResponse('OK')
            else:
                # no response delegates to _admittedGet()
                return self._admittedGet(request)
        elif not isinstance(response, HttpResponseForbidden):
            self.trackHeartbeat(request)
        return response

    def get(self, request, *args, **kwargs):
        if not self._isRequestAdmitted(request, *args):
            return HttpResponseForbidden() if self.updateMode else render(request, 'durak/admit.html')
        elif self.updateMode:
            return super().get(request, *args, **kwargs)
        else:
            return self._admittedGet(request)

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
            not args and
            checkIn is not None and
            checkIn.id == gameId and
            playerId in checkIn.tokens
        )
        if passed and not self.updateMode:
            passed = not checkIn.game or not checkIn.game.playing
        if passed:
            self.heartbeat(playerId)
            self.checkIn = checkIn
        return passed

    def getPAM(self):
        """
        Retrieve a reference to the Pluggable Authentication Module
        (PAM) configured for the application.

        The application looks up a PAM reference in the
        ``CARDS_AUTHENTICATOR`` Django setting. If that setting
        is absent, authenticator class ``LocalClientAuthenticator``
        from the `cards_web.connect` module is returned by default.
        Otherwise, the value must be a sequence of two elements: a
        fully qualified module name on the application's path, and
        the name of the authenticator class or function compliant
        with requirements of `cards_web.connect.Authenticator`.

        Returns
        -------
        cards_web.connect.Authenticator | callable
            a reference to the configured or default authenticator

        Notes
        -----
            Pluggable Authentication Modules used with this application
            **must** support synchronous authentication mode.
        """
        if not hasattr(settings, 'CARDS_AUTHENTICATOR'):
            return local_client_authenticator
        ref = settings.CARDS_AUTHENTICATOR
        if not isinstance(ref, collections.Sequence) or \
             type(ref) is str:
            raise TypeError('CARDS_AUTHENTICATOR setting'
                            ' must be a non-string sequence, got: '
                            + type(ref).__name__)
        try:
            module = importlib.import_module(ref[0])
            auth = getattr(module, ref[1])
        except:
            raise ValueError('CARDS_AUTHENTICATOR setting is'
                             ' not valid: ' + repr(ref))
        if not issubclass(auth, Authenticator) and \
             not callable(auth):
            raise TypeError('CARDS_AUTHENTICATOR setting'
                            ' must point to a class derived from'
                            ' `cards_web.connect.Authenticator` or'
                            ' a function, got: '
                            + repr(auth))
        return auth
        
    def _admitRequest(self, request, *args):
        """
        Process a request to admit new player to a game table.

        Parameters
        ----------
        request : django.http.HttpRequest
            The admission request.
        args : collections.Sequence
            Values of arguments parsed from the URL path. 

        Returns
        -------
        django.http.HttpResponse | NoneType
            The application's response, usually an error or redirect, or
            ``None`` if this view should respond via `_admittedGet`.
        """

        log = logging.getLogger(type(self).__module__)
        try:
#             if settings.DEBUG:
#                 if request.user.is_authenticated:
#                     log.debug('User is authenticated as %s', request.user.username)
#                 else:
#                     log.debug('User is not authenticated!')
            authenticated = (self.getPAM())(request, *args)   
            admitted = None
            token = request.session.get(self.PLAYER_IN_SESSION)
            if token is None and args:
                token = args[0]
            gameIdCandidate = request.session.get(self.GAME_IN_SESSION)
            # TODO: for thread safety, the model must be locked.
            if gameIdCandidate is None:
                checkIn = PlayerCheckIn.FACILITIES.get(token)
                gameIdCandidate = None if checkIn is None else checkIn.id
            else:
                checkIn = PlayerCheckIn.FACILITIES.get(gameIdCandidate)

            if checkIn is None:
                checkIn = PlayerCheckIn.ACTIVE_FACILITY()

            if not (checkIn is None or
                    gameIdCandidate is None and authenticated):
                playerNo = checkIn.tokens.get(token)
                playerOrToken = (None if playerNo is None else
                    checkIn.fetchPlayer(playerNo))
                if (playerNo is not None and token == playerOrToken):
                    checkIn.fetchPlayer(playerNo, token)
                elif (isinstance(playerOrToken, RemoteEntity)
                     and playerOrToken.offline):
                    checkIn.playerConnectionStatus(token, True)
                else:
                    playerOrToken = None
                if playerOrToken is not None:
                    request.session[self.PLAYER_IN_SESSION] = token
                    admitted = True
            elif authenticated:
                if checkIn is None:
                    checkIn = PlayerCheckIn()
                playerOrToken = checkIn.fetchPlayer(0)
                if type(playerOrToken) is str:
                    checkIn.fetchPlayer(token = playerOrToken)
                elif (isinstance(playerOrToken, RemoteEntity)
                     and playerOrToken.offline):
                    playerOrToken = checkIn.id
                    checkIn.playerConnectionStatus(playerOrToken, True)
                if type(playerOrToken) is str:
                    request.session[self.PLAYER_IN_SESSION] = token = playerOrToken
                    admitted = True
    
            if admitted:
                log.info('Admitted client "%s" at %s with token "%s"',
                         request.META.get('HTTP_USER_AGENT'),
                         request.META['REMOTE_ADDR'], token)
                self._userId = token
                request.session[self.GAME_IN_SESSION] = checkIn.id
                self.updateSessionKey(token, request.session)
                self.cometyDispatcher = self.cometyDispatcherFor(request, *args)
                self.cometyDispatcher.registerUser(token, False)
                target = None
                if checkIn.game and checkIn.game.playing:
                    # if the game is on, send re-joining player to the table
                    target = django.urls.reverse('table')
                elif args:
                    suffix = django.urls.reverse('intro', args = args)
                    if request.path.endswith(suffix):
                        target = request.path[0:-len(suffix)]
                        target += django.urls.reverse('intro')
                self.trackHeartbeat(request)
                return None if target is None else HttpResponseRedirect(target)
            else:
                # TODO: adorn this with the page template
                return HttpResponseForbidden(_(
'''You entered an invalid URL or had this page open in multiple browser windows.
 Please check the URL or use the existing window with this application.'''
                ), content_type='text/plain; charset=utf-8')
        except:
            log.error('Error authorizing invitation with argument(s): %s',
                      args, exc_info=True)
            return HttpResponseServerError()

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

        response = None
        if 'action' in request.GET:
            action = request.GET.get('action')
            response = self._handleAction(action, request)
        if response is not None:
            self.trackHeartbeat(request)
            return response
        userId = request.session[self.PLAYER_IN_SESSION]
        checkIn = PlayerCheckIn.FACILITIES[userId]
        try:
            ui = checkIn.getUiDispatcher()
            ui.confirmEvents(userId)
            serverName = request.META['SERVER_NAME']
            # TODO: set `defaultPort` to None when it equals standard port for the protocol
            defaultPort = request.META['SERVER_PORT']
            inboundAddresses = self._getInboundAddresses(serverName)
            playerNo = checkIn.tokens[userId]
            countRange = list(WebGame.getPlayerCountRange(checkIn.gameSettings))
            if countRange[1] is None:
                countRange[1] = durak_ws.table.TableView.SEATING_CAPACITY
            else:
                countRange[1] = min(countRange[1], durak_ws.table.TableView.SEATING_CAPACITY)
            contextVars = {
                'bodyClass' : "table-background",
                'checkin' : checkIn,
                'gameApp' : 'durak',
                'playerCountRange' : countRange,
                'lowCardRankRange' : WebGame.getLowestCardRankRange(checkIn.gameSettings),
                'inboundAddresses' : inboundAddresses,
                'inboundAddressOther' : type(checkIn.host) is str
                    and (checkIn.host != serverName
                        or inboundAddresses[-1][0] != serverName),
                'playerNo' : playerNo,
                'URLPrefix' : self.getURLPrefix(request, checkIn, defaultPort),
                'error' : request.session.get(self.ERROR_IN_SESSION),
                'showBanner' : request.session.get(self.SHOW_RESULT_IN_SESSION, False),
            }
            response = render(request, 'durak/intro.html', contextVars,
#            RequestContext(request,
#            processors=[self.remoteIpAddressProcessor])
            )
            if self.ERROR_IN_SESSION in request.session:
                del request.session[self.ERROR_IN_SESSION]
            self.clearDelayStats(request.session)
            self.trackHeartbeat(request, True)
            return response
        except:
            log = logging.getLogger(type(self).__module__)
            log.error('Error serving %s to user "%s"', type(self).__name__,
                      userId, exc_info=True)
            return HttpResponseServerError()

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
        return (checkIn.getUiDispatcher()
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

    def disconnectSession(self, session): # TODO: reuse in the game table view
        """
        Invalidate an inactive session to allow a player to
        reconnect. 
        
        Invalidates a session by removing the variable with
        `GAME_IN_SESSION` key.
        This method should be called when the application
        detects that a player has disconnected.
        Call `sessionByUser` first to retrieve
        the player's session object.
        
        Parameters
        ----------
        session : django.contrib.sessions.backends.base.SessionBase
            The session object deemed inactive.
    
        Raises
        ------
        KeyError
            If there is no mapping for `GAME_IN_SESSION` key
            in the passed session.
    
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

        del session[self.GAME_IN_SESSION]
        session.save()

    _inboundAddresses = None

    @classmethod
    def _getInboundAddresses(class_, serverName = None):
        """
        Prepare contents of `models.InboundAddressEnumerator` for
        display on the web form.

        This method generates a tuple of `(index, label)` tuples
        from `models.InboundAddressEnumerator` contents and allows
        for appending the ``SERVER_NAME`` value from an HTTP request
        if it differs from the local host's name. The index of such
        ``SERVER_NAME`` string is that string itself prefixed with
        ``:``.   
        """
        if class_._inboundAddresses is None:
            inboundAddresses = []
            uniqueInboundAddresses = set()
            i = 0
            for addrTuple in InboundAddressEnumerator.FACILITY:
                inboundAddresses.append((i, addrTuple[0]))
                uniqueInboundAddresses.add(addrTuple[1:3])
                i += 1
            if serverName is not None and (
                   None, serverName) not in uniqueInboundAddresses:
                inboundAddresses.append((':' + serverName, serverName))
            class_._inboundAddresses = tuple(inboundAddresses)
        return class_._inboundAddresses

    @staticmethod
    def getURLPrefix(request, checkin, defaultPort = None):
        """
        Build the application's URL prefix.
        
        
        Parameters
        ----------
        request : django.http.HttpRequest
            The web request being processed.
        checkin : models.PlayerCheckIn
            Facility that admits players into the current game.
        defaultPort : int, optional
            The port number to be added to the invitation URLs when `port`
            property is not set. Omit when using the standard port number for
            the client's protocol.

        Returns
        -------
        str
            The application's URL prefix.
        """

        protocol = 'https' if request.is_secure() else 'http'
        if type(checkin.host) is str:
            netloc = checkin.host
        else:
            addrInfo = InboundAddressEnumerator.FACILITY[checkin.host]
            netloc = addrInfo[2]
            if socket.AF_INET6 == addrInfo[1]:
                netloc = "[%s]" % netloc
        if checkin.port is not None:
            netloc += ':%s' % checkin.port
        elif defaultPort is not None:
            netloc += ':%s' % defaultPort
        return urlunsplit((
            protocol,
            netloc,
            '', '', ''
        ))
