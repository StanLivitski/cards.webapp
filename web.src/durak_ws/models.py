# vim:fileencoding=UTF-8 
#
# Copyright © 2015, 2017 Stan Livitski
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
    Classes that implement check-in of players via this web
    application and connect interactive players to the game
    model.
    
    TODOD <Extended description>

    Key elements
    ------------
    PlayerCheckIn : Implements check-in of players into this
        web application.
[
    <python_name> : <One-line summary of a class, exception,
    function, or any other object exported by the module and
    named on this line.>
    ...
]

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
import logging
import math
import queue
import random
import socket
import sys
import threading
import netifaces

from django.utils.translation import ugettext_lazy as _

import cards.game
import cards.durak
import comety
import collections
import mapping

class InboundAddressEnumerator(collections.Sequence):
    """
    Contains list of names and addresses that can be used
    to connect to this host by other network devices and provides
    some additional network address information. 
    
    This class follows the singleton pattern, which means you don't
    create any instances thereof. This module will create the only 
    object of this class and store it in the `FACILITY` class variable.
    Use that instance to determine this host's external names and
    addresses on the network. The results are represented as a
    read-only sequence of ``(label, family, address)`` tuples,
    where:
    
    - ``label`` is the human-readable label of the item
    - ``family`` is either an ``AF_*`` constant from the
      `socket` module if the item contains an address, or
      ``None`` if the item contains a network name
    - ``address`` is either a network name or an address
      in its family-specific string format

    The `FACILITY` sequence is guaranteed to have at least one element:
    this host's name returned by `socket.gethostname`(). If
    `socket.fqdn`() reports a different value, it will be added
    to the sequence as well.

    Additionally, this class has static methods that provide
    network address information. Those methods are summarized
    below.

    Methods
    ---------------
    resolve(nameOrAddress, type_):
        Resolve a host name into network addresses(es) or convert
        addresses(es) to the canonical format
    isLoopbackAddress(family, address, strict):
        Tell whether a network address belongs to a loopback device.

    Raises
    ----------
    RuntimeError
        When an attempt is made to create an additional instance of this
        type.

    Notes
    ----------
    This class uses the `netifaces <https://pypi.python.org/pypi/netifaces/>`
    library to determine the host's external addresses in a way that works
    across platforms. ``netifaces`` does not declare the native symbols it
    exports in the Python code, which causes ``Undefined variable from import``
    warnings in the code below. These warnings may be ignored until
    ``netifaces`` is fixed to declare its sybmols properly.

    Examples
    ----------------
    >>> enum = InboundAddressEnumerator.FACILITY
    >>> len(enum) > 0
    True
    >>> all( type(a) is tuple for a in enum )
    True
    >>> all( len(a) == 3 for a in enum )
    True
    """
    FACILITY = None

    def __init__(self):
        if type(self).FACILITY is not None:
            raise RuntimeError('Class %s can only have one instance'
                                % type(self).__name__)
        items = self._items = []
        names = collections.OrderedDict.fromkeys(
             (socket.getfqdn(), socket.gethostname())
        )
        addrs = collections.OrderedDict()
        for name in names:
            if name: 
                items.append((name, None, name))
                for addr in self.resolve(name, socket.SOCK_STREAM):
                    addrKey = addr[1:3]
                    if self.isLoopbackAddress(*addrKey) is False:
                        addrs[addrKey] = addr
        for iface in netifaces.interfaces():
            ifaceAddrs = netifaces.ifaddresses(iface)
            for family in (socket.AF_INET, socket.AF_INET6):
                if family not in ifaceAddrs:
                    continue
                for info in ifaceAddrs[family]:
                    addr = info['addr']
                    if not self.isLoopbackAddress(family, addr):
                        addrs[(family, addr)] = (
                            ('' if iface.startswith('{') else iface + ' ')
                            + addr,
                            family,
                            addr   
                        )
        items.extend(addrs.values())

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        return self._items[key]

    @staticmethod
    def resolve(nameOrAddress = None, type_ = 0):
        """
        Resolve a host name into network addresses(es) or convert
        addresses(es) to the canonical format.
        
        Calls `socket.getaddrinfo` to determine a host's address(es)
        with the available network protocols.

        Parameters
        ----------
        nameOrAddress : str, optional
            A host name or string address to resolve or convert.
            The default of ``None`` causes this method to obtain
            loopback addresses(es) of this host.
    
        Yields    
        ------
        tuple
            Tuples with the same elements as those contained in
            `InboundAddressEnumerator` objects.
    
        Other parameters
        ----------------
        type_ : int, optional
            Preferred socket type, for example `socket.SOCK_STREAM`
            or `socket.SOCK_DGRAM`. The default value ``0`` means
            that socket addresses of any type can be returned.
    
    [    Raises
        ------
        <exception_type>
            <Description of an error that may get raised and under what conditions.
            List only errors that are non-obvious or have a large chance of getting raised.>
        ... ]
    
    [    See Also
        --------    
        <python_name> : <Description of code referred by this line
        and how it is related to the documented code.>
         ... ]
    
        Examples
        --------
        >>> not tuple(InboundAddressEnumerator.resolve())
        False
        >>> ('127.0.0.1',2,'127.0.0.1') in set(InboundAddressEnumerator.resolve())
        True
        """
        infos = socket.getaddrinfo(nameOrAddress, 0, type = type_)
        for info in infos:
            yield (info[4][0], info[0], info[4][0])

    @staticmethod
    def isLoopbackAddress(family, address, strict = False):
        """
        Tell whether a network address belongs to a loopback device.

        
        Parameters
        ----------
        family : int
            an ``AF_*`` constant from the `socket` module
        address : str
            a network address in its family-specific string format
    
        Returns
        -------
        bool | NoneType
            Whether a network address belongs to a loopback device.
            This can be ``None`` if ``family`` is not supported and
            ``strict`` is ``False``.
    
        Other parameters
        ----------------
        strict : bool, optional
            Set this to ``true`` to raise an exception when ``family``
            is not supported by this method.

        Raises
        ------
        socket.error
            If the address value is not valid.
        NotImplementedError
            If ``family`` is not supported and``strict`` is ``True``.
    
        Examples
        --------
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_INET, '127.0.0.1')
        True
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_INET, '127.100.1.1', True)
        True
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_INET, '100.1.1.127', True)
        False
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_UNSPEC, 'loopback') is None
        True
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_UNSPEC, 'loopback', True
        ...  ) is None  #doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotImplementedError: Unsupported network address family ...
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_INET6, '2001:db8::ace1')
        False
        >>> InboundAddressEnumerator.isLoopbackAddress(socket.AF_INET6, '::1')
        True
        """
        tests = {
            socket.AF_INET: lambda addr: socket.inet_aton(addr)[0] == 127,
            socket.AF_INET6: lambda addr: addr == '::1', 
        }
        if family in tests:
            return tests[family](address)
        elif strict:
            raise NotImplementedError(
              'Unsupported network address family %d' % family
            )
        else:
            return None

InboundAddressEnumerator.FACILITY = InboundAddressEnumerator()

class PlayerCheckIn:
    """
    Admits players into this web application and sets up a new game.
    
    Use an object of this class to record names and session tokens
    of players who will be joining a game. Once all seats are taken,
    the object can be used to generate a dictionary of parameters to
    be passed to the new game constructor.

    Parameters
    ----------
    gameType : type, optional
        A concrete class that implements the game to be played.
        This must be a subclass of `cards.game.Game` with a constructor
        having the same signature. Defaults to `WebGame` if omitted. 

    Attributes
    -----------------
    capacity
    gameSettings
    game
    id
    host
    playerStata
    ready
    port
    tokens
    uiDispatcher
    chatDispatcher : comety.Dispatcher
        Comety dispatcher for sending chat messages between players.
        Players registered with the dispatcher using their tokens, when
        such tokens are created, and never unregistered, so messages from
        a player who left may still be delivered.
    FACILITIES : collections.Mapping
        A class variable containing player ids mapped to objects of this
        type used to set up games for those players. Since a game id is
        equal to one of its' players ids (see `getId`), this mapping will
        also return objects of this type by their game ids.
    PLAYER_STATA : tuple
        English messages corresponding to numeric status values
        in `playerStata`.
    LOCALIZED_PLAYER_STATA : tuple
        Deferred localized messages corresponding to numeric status values
        in `playerStata`.
    PLAYER_STATA_CODES : collections.Mapping
        An immutable mapping of english messages to numeric
        status values.

[
    <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
    fetchPlayer(playerNo, token)
        Return a player object for a table position or token.
    createPlayer(playerNo, token)
        Override to create custom player objects when `fetchPlayer`()
        is called in a subclass.
    createToken(length)
        Create a random token to be assigned to a new player.
    modifyToken(token)
        Modify a random token to avoid clashing with existing tokens.
    createTokens(count,length)
        Creates multiple tokens that do not duplicate any tokens stored
        herein.
    ACTIVE_FACILITY()
        Returns the "active" instance of this class used to set up
        the next game.
    close(self):
        Wrap up the check-in process and create the game
        model object.
[    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

    Raises
    ----------
    RuntimeError
        When an attempt is made to create an additional instance of this
        type.

    See Also
    --------------
    cards.game.Game : Use this object as the `playerFactory` argument
        when creating a game.

    Examples
    ----------------
    >>> from cards.durak import Game
    >>> checkIn = PlayerCheckIn(Game)
    >>> len(checkIn.tokens) == checkIn.capacity
    True
    >>> len(checkIn.gameSettings['players']) == checkIn.capacity
    True
    >>> PlayerCheckIn.ACTIVE_FACILITY() is None
    False
    """

    PLAYER_STATA = (
        'you',
        'expected',
        'joined',
    )

    PLAYER_STATA_CODES = mapping.ImmutableMap(dict(
        reversed(item) for item in enumerate(PLAYER_STATA)
    ))

    LOCALIZED_PLAYER_STATA = tuple(
        _(status) for status in PLAYER_STATA
    )

    PLAYER_UPDATE_EVENT = 'player-update'
    PLAYER_STATUS_EVENT = 'player-status'
    SETTINGS_UPDATE_EVENT = 'settings-update'
    READY_STATE_EVENT = 'ready-state'
    GAME_START_EVENT = 'game-start'

    FACILITIES = dict()

    @classmethod
    def ACTIVE_FACILITY(cls):
        """
        Returns the "active" instance of this class used to set up
        the next game. 
        
        There can be at most one "active" instance of this class at
        any given time. When there are no instances of this class,
        the first instance created becomes active.
    
        Returns
        -------
        NoneType | PlayerCheckIn
            The "active" instance of this class, if it exists.
            Returned instance shall be mutable until `close`d. 
    
    [    See Also
        --------    
        <python_name> : <Description of code referred by this line
        and how it is related to the documented code.>
         ... ]
    
        Examples
        --------
        >>> import collections
        >>> from cards.durak import Game
        >>> del PlayerCheckIn._activeFacilityId
        >>> PlayerCheckIn.FACILITIES.clear()
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn1 = PlayerCheckIn(Game)
        >>> PlayerCheckIn.ACTIVE_FACILITY() is checkIn
        True
        >>> PlayerCheckIn.ACTIVE_FACILITY() is checkIn1
        False
        """

        if getattr(cls, '_activeFacilityId', None) is None:
            return None
        else:
            return cls.FACILITIES[cls._activeFacilityId]

    def __str__(self):
        return type(self).__name__

    def __init__(self, gameType = None):
        self._gameType = WebGame if gameType is None else gameType
        self._comety = None
        self._game = None
        self._settings = self._gameType.defaults() 
        count = self._settings['players'] # documented at `getCapacity`
        self._players = [ None ] * count
        # values are tuples of ``(token, player object)`` for established sessions,
        # tuples of ``(token,)`` otherwise
        self.chatDispatcher = comety.Dispatcher()
        self._tokens = {} # values are players' positions at the table
        i = 0
        for token in self.createTokens(count):
            self._tokens[token] = i
            self._players[i] = (token,)
            self.FACILITIES[token] = self
            self.chatDispatcher.registerUser(token, False)
            i += 1
        cls = type(self)
        if getattr(cls, '_activeFacilityId', None) is None:
            cls._activeFacilityId = self.id
        self._host = 0
        self._port = None
        if self._comety is not None:
            self._comety.discard()
            self._comety = None

    def getId(self, playerNo = 0):
        """
        Return this object's identifier for correlating with players'
        sessions, or a specific player's token.

        The game's identifier is the first player's token. 
        
        Parameters
        ----------
        playerNo : int, optional
            integer index, or position at the table, of a player
            whose token shall be retrieved.

        Returns
        -------
        str
            This object's unique session identifier, or a requested
            player's token.

        Notes
        -----
        This property was added to allow for multiple check-in
        facilities in future.  

        See Also
        --------
        fetchPlayer : allows callers to initialize this property
            by creating a player object with seat index ``0``.

        Examples
        --------
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> type(checkIn.id) is str
        True
        >>> len(checkIn.id)
        5
        >>> all( letter in PlayerCheckIn._TOKEN_ALPHABET
        ...  for letter in checkIn.id)
        True
        """

        info = self._players[playerNo]
        return info[0]

    id = property(getId)

    def getUiDispatcher(self):
        """
        Return the `comety` UI dispatcher referenced by this object.

        The UI dispatcher associated with this object enables the
        user introductions' web page to be updated in response to
        actions of other users, such as joining the table, sending
        messages, or changing settings.

        Returns
        -------
        comety.Dispatcher
            The UI dispatcher associated with this object. The
            dispatcher is created lazily when this property is first
            read, and doesn't change.

        Examples
        --------
        TODOD: tests
        """

        if self._comety is None:
            self._comety = comety.Dispatcher()
        return self._comety

    uiDispatcher = property(getUiDispatcher)

    def getGameSettings(self):
        """
        Obtain a settings' map for making a new game
        object or querying that class for settings' constraints.

        Currently, all returned settings are the defaults for the
        game class, except `players`, which is an
        iterable over `cards.game.Player` instances connected to
        players that use this web application, or `None` values
        for empty seats. Elements of `players` obtained through
        this method or property should be treated as read-only
        objects.

        Returns
        -------
        collections.Mapping
            An immutable map of the game settings configured herein.
    
        See Also
        --------------
        cards.game.Game : Use the returned map as the `userSettings`
            argument when constructing a game.

        Examples
        --------
        >>> import collections
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> isinstance(checkIn.gameSettings, collections.Mapping)
        True
        >>> playerCount = len(checkIn.gameSettings['players'])
        >>> all( i is None
        ...       for i in checkIn.gameSettings['players'])
        True
        >>> all( isinstance(
        ...       checkIn.fetchPlayer(token=token),
        ...       cards.game.Player)
        ...  for token in checkIn.tokens
        ... )
        True
        >>> all( isinstance(i, cards.game.Player)
        ...       for i in checkIn.gameSettings['players'])
        True
        >>> playerCount == len(checkIn.gameSettings['players'])
        True
        """

        settings = self._settings
        if isinstance(settings, mapping.ImmutableMap):
            return settings
        players = [ (info[1] if 1 < len(info) else None
                    ) for info in self._players ]
        settings['players'] = players
        return mapping.ImmutableMap(settings)

    gameSettings = property(getGameSettings)

    def updatePlayer(self, _token, **kwargs):
        """
        Update a player object and notify attached Comety UIs.

        Calling this method is the preferred way to change the
        players' properties as it will notify other users
        about the change. When called with only the first argument,
        or all attempts to change properties on the player object
        fail, no event is posted to the Comety UIs.
        
        Parameters
        ----------
        _token : str
            string with session/invitation token of a player
            to be updated.
        
        Other parameters
        ----------------
        Any extra keyword arguments passed via the `kwargs` attribute
        are the property values to be assigned to the target player.
    
        Raises
        ------
        TypeError
            If the first argument is ``None`` or other improper type.
        ValueError
            If the token is not accepted, or no
            player object exists at that seat yet, or a value is
            not valid for its property.
        AttributeError
            If the player object will not accept a property assignment.
    
        See Also
        --------    
        tokens : Contains session/invitation tokens accepted by this
            facility.
        fetchPlayer() : Used to create new player objects when needed.
    
        Examples
        --------
        """

        if type(_token) is str:
            if _token not in self._tokens:
                raise ValueError('Unknown token: "%s"' % _token)
            playerNo = self._tokens[_token]
            player = self.fetchPlayer(playerNo)
        else:
            raise TypeError('Unsupported index or token type %s'
                            % type(_token).__name__)
        if not isinstance(player, cards.game.Player):
            raise ValueError('Player with token "%s" is missing.'
                        % str(_token))
        now = {}
        was = {}
        error = None
        for name in kwargs:
            try:
                was[name] = getattr(player, name)
            except:
                pass
            try:
                setattr(player, name, kwargs[name])
            except:
                log = logging.getLogger(type(self).__module__)
                log.error(
                    'Error assigning property "%s" = "%s" to player with token "%s"',
                    name, kwargs[name], _token, exc_info=True
                )
                if error is None:
                    error = sys.exc_info()[1]
            else:
                now[name] = kwargs[name]

        if now:
            self.uiDispatcher.postEvent(self,
                event = self.PLAYER_UPDATE_EVENT,
                index = playerNo, was = was, now = now)

        if error is not None:
            raise error

    def fetchPlayer(self, playerNo = None, token = None):
        """
        Return a player object for a table position or token.
        
        Fetches a `cards.game.Player` object by its index
        (position at the table) or session/invitation token.
        When looking up player by token, a new player
        object will be created if the token is accepted, but no
        player object has yet taken the seat with
        that token. When looking up player by index, a token
        is returned when the seat is empty. When ``token`` argument
        is passed, the ``playerNo`` argument is ignored. Note that
        one of the above arguments is always required.
        
        Parameters
        ----------
        playerNo : int, optional
            integer index, or position at the table, of a player
            to be retrieved. If the ``token`` argument is
            present, this argument is ignored.
        token : str, optional
            a string with session/invitation token of a player
            to be retrieved. If the token is accepted, but no
            player object exists at that seat yet, a new player object
            is created and returned. This argument must be present if the
            ``playerNo`` argument is omitted or ``None``. When this
            argument is present, the ``playerNo`` argument is ignored.
    
        Returns
        -------
        cards.game.Player | str
            The `cards.game.Player` object associated with the
            arguments. When only the ``playerNo`` argument is passed,
            this may be a token string assigned to the empty seat with
            that number.
    
        Raises
        ------
        TypeError
            If both arguments are missing or ``None``.
        IndexError
            If ``playerNo`` argument is out of range.
        ValueError
            If the ``token`` argument is not accepted.
    
        See Also
        --------    
        tokens : Contains session/invitation tokens accepted by this
            facility.
        createPlayer() : Used to create new player objects when needed.
    
        Examples
        --------
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> all( (checkIn.tokens[
        ...   checkIn.fetchPlayer(i)] == i)
        ...  for i in range(checkIn.capacity) )
        True
        >>> checkIn.capacity = 5
        >>> all( (checkIn.tokens[
        ...   checkIn.fetchPlayer(i)] == i)
        ...  for i in range(checkIn.capacity) )
        True
        >>> all( isinstance(
        ...       checkIn.fetchPlayer(token=token),
        ...       cards.game.Player)
        ...  for token in checkIn.tokens
        ... )
        True
        >>> all( isinstance(checkIn.fetchPlayer(i),
        ...       cards.game.Player)
        ...  for i in range(checkIn.capacity) )
        True
        >>> checkIn.fetchPlayer()
        Traceback (most recent call last):
        ...
        TypeError: `fetchPlayer()` is called without arguments
        >>> checkIn.fetchPlayer(-1)
        Traceback (most recent call last):
        ...
        IndexError: `playerNo` must be a positive number less than 5, got: -1
        >>> checkIn.fetchPlayer(playerNo=6)
        Traceback (most recent call last):
        ...
        IndexError: `playerNo` must be a positive number less than 5, got: 6
        >>> checkIn.fetchPlayer(token=
        ...  [ token for token in checkIn.createTokens(1) ][0]
        ... )  #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        ValueError: Unknown token: "..."
        """

        if token is None:
            if playerNo is None:
                raise TypeError('`fetchPlayer()` is called without arguments')
            elif 0 <= playerNo < len(self._players):
                playerInfo = self._players[playerNo]
                return playerInfo[1] if 1 < len(playerInfo) else playerInfo[0]
            else:
                raise IndexError(
                    '`playerNo` must be a positive number less than %d, got: %d'
                    % (len(self._players), playerNo)
                )
        else:
            if token in self._tokens:
                playerNo = self._tokens[token]
                player = self.fetchPlayer(playerNo)
                if not isinstance(player, cards.game.Player):
                    wasReady = self.ready
                    player = self.createPlayer(playerNo, token)
                    assert isinstance(player, cards.game.Player)
                    self._players[playerNo] = (token, player)
                    self._onPlayerStatusChange(playerNo, 'joined', wasReady)
                return player
            else:
                raise ValueError('Unknown token: "%s"' % token)

    def _onPlayerStatusChange(self, playerNo, status, wasReady):
        self.uiDispatcher.postEvent(self,
            event = self.PLAYER_STATUS_EVENT,
            index = playerNo,
            status = _(status)
        )
        ready = self.ready
        if wasReady != ready:
            self.uiDispatcher.postEvent(self,
                event = self.READY_STATE_EVENT,
                ready = ready
            )
           

    def createPlayer(self, playerNo, token):
        """
        Override to create custom player objects when `fetchPlayer`()
        is called in a subclass.
        
        This method **should not** be called directly as it will not
        store a reference to the returned object anywhere. The default
        implementation creates and returns a `cards.game.Player` object
        of type specified by the game class with `RemoteEntity` mixin
        regardless of the arguments.
        
        Parameters
        ----------
        playerNo : int
            integer index, or position at the table, of a player
            to be created.
        token : str
            a string with session/invitation token of a player
            to be created.

        Returns
        -------
        cards.game.Player
            the new player object of a subtype of `cards.game.Player`
            class
        """

        return WebPlayer()

    def playerConnectionStatus(self, token, connected = False):
        """
        Change a remote player's connection status.
        
        Marks a player as either connected or disconnected. The player
        to be marked must be a `RemoteEntity`.
        Looks up a player to be marked by its token. 
        
        Parameters
        ----------
        token : str
            a string with session/invitation token of a player
            that is no longer connected.

        Raises
        ------
        ValueError
            If the ``token`` argument is not accepted.
        TypeError
            If the player with that token is not a `RemoteEntity`.
        """

        if token in self._tokens:
            wasReady = self.ready
            playerNo = self._tokens[token]
            player = self.fetchPlayer(playerNo)
            if not isinstance(player, RemoteEntity):
                raise TypeError(
                    'Unsupported player type %s at seat %d, token "%s"'
                    % (type(player).__name__, playerNo, token))
            player.offline = not connected
            self._onPlayerStatusChange(playerNo, 'joined' if connected else 'expected', wasReady)
        else:
            raise ValueError('Unknown token: "%s"' % token)       

    def close(self):
        """
        Wrap up the check-in process and create the
        game model object. 
        
        This method creates a game as configured herein,
        starts it and stores a reference in the `game` property.
        A successful call disables changes to this object's
        properties related to the game's settings. It also
        retires this object as an `ACTIVE_FACILITY`.
    
        Raises
        ------
        RuntimeError
            If this object is not ready to start a game.
            A new game can be started when all players have
            joined. This method may return successfully when
            some players are offline, even though `ready` will
            be ``False`` in that case.
        Exception
            Any exception raised by the game's ``start`` method.
    
        See Also
        --------    
        game : References the game object configured herein.
        ready : Property that tells whether this method can be
            called.
        gameSettings : References the settings that were, or will be,
            passed to the new game object.
    
    [    Notes
        -----
        <Additional information about the code, possibly including
        a discussion of the algorithm. Follow it with a 'References'
        section if citing any references.>
        ]
    
        Examples
        --------
        >>> import collections
        >>> from cards.durak import Game
        >>> del PlayerCheckIn._activeFacilityId
        >>> checkIn = PlayerCheckIn(Game)
        >>> PlayerCheckIn.ACTIVE_FACILITY() is checkIn
        True
        >>> checkIn.close()
        Traceback (most recent call last):
        ...
        RuntimeError: Not ready to start the game: player(s) [0, 1] are missing
        >>> for token in checkIn.tokens:
        ...  player = checkIn.fetchPlayer(token=token)
        >>> checkIn.close()
        >>> PlayerCheckIn.ACTIVE_FACILITY() is checkIn
        False
        >>> type(checkIn.game) is Game
        True
        >>> checkIn.capacity = 5  #doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: ...
        """

        settings = self.gameSettings
        players = settings['players']
        if any(player is None for player in players):
            raise RuntimeError(
                'Not ready to start the game: player(s) %s are missing'
                % [ i for i in range(len(players)) if players[i] is None ]
                )
        game = self._gameType(None, uiDispatcher=self.uiDispatcher, **settings)
        game.start()
        self._settings = settings # freezes settings as a side-effect
        self._game = game
        cls = type(self)
        if getattr(cls, '_activeFacilityId', None) == self.id:
            cls._activeFacilityId = None
        self.uiDispatcher.postEvent(self, event = self.GAME_START_EVENT)

    @property
    def game(self):
        """
        Return the game object configured herein.
        
        This property references the game object created by `close`
        method above.
        
        Returns
        -------
        cards.game.Game | NoneType
            The game object configured herein and created by `close`
            method, or ``None`` if this object is not yet `close`d.
    
        See Also
        --------    
        close : Must be called before this property returns anything.
    
        Examples
        --------
        >>> import collections
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn.game is None
        True
        >>> for token in checkIn.tokens:
        ...  player = checkIn.fetchPlayer(token=token)
        >>> checkIn.close()
        >>> type(checkIn.game) is Game
        True
        >>> checkIn.game.defendant is None
        False
        >>> checkIn.game.attacker is None
        False
        >>> checkIn.game.defendant == checkIn.game.attacker
        False
        """

        return self._game

    def opponentMap(self, position, seatCount):
        """
        Return the mapping of opponents' positions to respective
        player objects configured herein.
        
        This property references player objects created by `close`
        method above.

        Parameters
        ----------
        position : int
            0-based position of the current player at the table.
        seatCount : int
            The largest number of players that the application can
            display.

        Returns
        -------
        collections.Mapping
            A map with keys equal to relative 1-based opponents'
            positions at the table to player objects within the game
            configured herein.
    
        See Also
        --------    
        close : Must be called before this method returns anything.
    
        Raises
        ----------
        ValueError
            if `seatCount` is less than the number of players,
            or `position` is out of range for the game
        RuntimeError
            if this object is not yet `close`d.
    
        Examples
        --------
        >>> import collections
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> for token in checkIn.tokens:
        ...  player = checkIn.fetchPlayer(token=token)
        >>> checkIn.opponentMap(0,2)
        Traceback (most recent call last):
        ...
        RuntimeError: Must close the check-in process and start the game first
        >>> checkIn.close()
        >>> map = checkIn.opponentMap(0,1)
        Traceback (most recent call last):
        ...
        ValueError: 2 player(s) are trying to take 1 seats
        >>> map = checkIn.opponentMap(0,2)
        >>> len(map)
        1
        >>> 1 in map
        True
        >>> map[1] is checkIn.game.players[1]
        True
        >>> map = checkIn.opponentMap(1,8)
        >>> len(map)
        1
        >>> 4 in map
        True
        >>> map[4] is checkIn.game.players[0]
        True
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn.capacity = 5 
        >>> for token in checkIn.tokens:
        ...  player = checkIn.fetchPlayer(token=token)
        >>> checkIn.close()
        >>> map = checkIn.opponentMap(1,8)
        >>> len(map)
        4
        >>> set(map.keys()) - {2, 4, 5, 7}
        set()
        >>> map[2] is checkIn.game.players[2]
        True
        >>> map[4] is checkIn.game.players[3]
        True
        >>> map[5] is checkIn.game.players[4]
        True
        >>> map[7] is checkIn.game.players[0]
        True
        """

        game = self.game
        if game is None:
            raise RuntimeError(
                'Must close the check-in process and start the game first'
            )
        playerCount = len(game.players)
        if playerCount > seatCount:
            raise ValueError(
                '%d player(s) are trying to take %d seats'
                % (playerCount, seatCount)
            )
        if not 0 <= position < playerCount:
            raise ValueError(
                'Position %d is out of range (0, %d)'
                % (position, playerCount)
            )
        balance = 0
        opponentMap = {}
        for seat in range(seatCount):
            if 0 >= balance:
                balance += seatCount
                if 0 < seat:
                    position += 1
                    if playerCount <= position:
                        position = 0
                    opponentMap[seat] = game.players[position]
            balance -= playerCount
        assert len(opponentMap) == playerCount - 1
        return opponentMap

    def getCapacity(self):
        """
        The number of players that will be invited to join the new
        game.

        The default value of this property is the same as default
        value of the `players` setting of `cards.game.Game`.

        Examples
        --------
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn.capacity
        2
        """

        return len(self._players)

    def setCapacity(self, newCapacity):
        """
        Changes the number of players that will be invited to join the
        new game.

        If the new capacity value is less than the current one, all data
        about players with indexes that exceed the new capacity is
        deleted from this object. If the new capacity value is greater
        than the current one, extra seats with indexes in
        ``range(capacity, newCapacity)`` are added to accommodate
        new players, and new tokens are assigned to those places.
    
        Parameters
        ----------
        newCapacity : int
            The new number of players that will be allowed to join
            the game. This number must be greater than 1 and less
            or equal to the maximum number of hands that can be dealt
            for this game.

        Raises
        ----------
        ValueError
            When the argument is not an acceptable capacity value.
        TypeError
            When this object is `close`d and does not allow changes. 

        Examples
        --------
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn.capacity = 4
        >>> checkIn.capacity
        4
        >>> len(checkIn.tokens) == checkIn.capacity
        True
        >>> set(checkIn.tokens.values()) \\
        ...  == set(range(checkIn.capacity))
        True
        >>> all( len(token) == 5 for token in checkIn.tokens )
        True
        >>> all( token in PlayerCheckIn.FACILITIES for token in checkIn.tokens )
        True
        >>> checkIn.capacity = 1
        Traceback (most recent call last):
        ...
        ValueError: Capacity value 1 must be at least 2, but no greater than 5
        >>> checkIn.capacity = 100
        Traceback (most recent call last):
        ...
        ValueError: Capacity value 100 must be at least 2, but no greater than 5
        >>> checkIn.capacity = 3
        >>> checkIn.capacity
        3
        >>> len(checkIn.tokens) == checkIn.capacity
        True
        >>> set(checkIn.tokens.values()) \\
        ...  == set(range(checkIn.capacity))
        True
        >>> all( len(token) == 5 for token in checkIn.tokens )
        True
        >>> all( token in PlayerCheckIn.FACILITIES for token in checkIn.tokens )
        True
        """

        minimum, maximum = self._gameType.getPlayerCountRange(self._settings)
        if not minimum <= newCapacity <= maximum:
            raise ValueError(
                'Capacity value %d must be at least %d, but no greater than %d'
                % ( newCapacity, minimum, maximum )
            )
        oldCapacity = i = len(self._players)
        if i > newCapacity:
            while i > newCapacity:
                i -= 1
                assert self._tokens[self._players[i][0]] == i
                token = self._players[i][0]
                del self._tokens[token]
                # del self.FACILITIES[token] # keep old token to avoid duplicates
            self._players = self._players[0:newCapacity]
        elif i < newCapacity:
            tokens = self.createTokens(newCapacity - i)
            for token in tokens:
                self._tokens[token] = i
                self._players.append((token,))
                self.FACILITIES[token] = self
                self.chatDispatcher.registerUser(token, False)
                i += 1
        self._settings['players'] = newCapacity
        if oldCapacity != newCapacity:           
            self.uiDispatcher.postEvent(self,
                event = self.SETTINGS_UPDATE_EVENT,
                was = {'players': oldCapacity},
                now = {'players': newCapacity}
            )

    capacity = property(getCapacity, setCapacity)

    def getLowestCardRank(self):
        """
        The lowest card rank that will be present on the game's
        deck.


        Examples
        --------
        >>> from cards.durak import Game
        >>> checkIn = PlayerCheckIn(Game)
        >>> checkIn.lowestCardRank
        6
        >>> checkIn.lowestCardRank = '2'
        >>> checkIn.lowestCardRank
        2
        >>> checkIn.lowestCardRank = '12'
        Traceback (most recent call last):
        ...
        ValueError: Unknown card rank: "12"
        """

        return self._settings['lowestRank']

    def setLowestCardRank(self, rank):
        cards.durak.Game.setLowestCardRank(self._settings, rank)

    lowestCardRank = property(getLowestCardRank, setLowestCardRank)

    def getHost(self):
        """
        Return the externally visible name, address, or an index into
        the `InboundAddressEnumerator.FACILITY` sequence used to build
        URLs distributed to remote players.

        Unless you change it with `setHost`, default value of this
        property is ``0``.

        Returns
        -------
        str | int
            Externally visible name or address of this host to include
            in URLs distributed to remote players. The value is a either a
            literal string or an integer index into the
            `InboundAddressEnumerator.FACILITY` sequence, no less than ``0``.
    
        See Also
        --------    
        InboundAddressEnumerator : the sequence indexed by this property
            if its value is an `int`. Its PyDoc describes how to decode
            such values before using them.
    
        Examples
        --------
        TODOdoc <In the doctest format, illustrate how to use this method.>
        """
        return self._host

    def setHost(self, host):
        """
        Change the externally visible name, address, or an index into
        the `InboundAddressEnumerator.FACILITY` sequence used to build
        URLs distributed to remote players.
        
        
        Parameters
        ----------
        host : str | int
            Externally visible name or address of this host to include
            in URLs distributed to remote players. The value should be an
            integer index into the `InboundAddressEnumerator.FACILITY`
            sequence or a literal string. If the value is less than ``0``,
            it is treated as an index from the tail of that sequence
            and converted to a positive index according to Python's
            conventions.  
    
        Raises
        ------
        IndexError
            If the supplied index is ouf of range with
            `InboundAddressEnumerator.FACILITY`.
    
        See Also
        --------    
        InboundAddressEnumerator : the sequence indexed by this property
            if its value is an `int`. Its PyDoc describes how to obtain
            such values before assigning them.
    
        Examples
        --------
        TODO <In the doctest format, illustrate how to use this method.>
        """
        if type(host) is not str:
            if type(host) is not int:
                raise TypeError(
                    'Value of %s is not valid for the `host` property'
                    % type(host)
                )
            elif host < 0:
                host += len(InboundAddressEnumerator.FACILITY)
            if not (0 <= host < len(InboundAddressEnumerator.FACILITY)):
                if 0 > host:
                    host -= len(InboundAddressEnumerator.FACILITY)
                raise IndexError(
                    ('Host index %d is out of range with'
                    + ' `InboundAddressEnumerator.FACILITY`')
                    % host
                )
        self._host = host

    host = property(getHost, setHost)

    def getPort(self):
        """
        Return this application's web service port number used to build
        URLs distributed to remote players.

        Unless you change it with `setPort`, default value of this
        property is ``None``.

        Returns
        -------
        NoneType | int
            This application's web service port number, an integer between ``0``
            and ``65536``, or ``None`` if the default port
            should be used instead.
    
        Examples
        --------
        TODO <In the doctest format, illustrate how to use this method.>
        """
        return self._port

    def setPort(self, port):
        """
        Change this application's web service port number used to build
        URLs distributed to remote players.
        
        
        Parameters
        ----------
        port : NoneType | int
            This application's web service port number to include
            in URLs distributed to remote players. The value should be an
            integer between ``0`` and ``65536``, or ``None`` if the default
            port number for the client's protocol shall be used.  
    
        Raises
        ------
        ValueError
            If the port number is ``0`` or less, or ``65536`` or greater.
    
        Examples
        --------
        TODO <In the doctest format, illustrate how to use this method.>
        """
        if port is None:
            pass
        elif type(port) is not int:
            raise TypeError(
                'Value of %s is not valid for the `port` property'
                % type(port)
            )
        elif not (0 < port < 65536):
            raise ValueError(
                'Port number %d is invalid'
                % port
            )
        self._port = port

    port = property(getPort, setPort)

    @property
    def playerStata(self):
        """
        A collection of players' introduction status tuples.
        
        Yields
        ------
        Tuples with ``(token, name, localizedStatus, statusCode)``
        values for each invited player.

        A tuple will contain `False` within its second element
        `name` if the player has not yet entered his/her name. 

        See also
        --------
        PLAYER_STATA_CODES : for explanation of status codes
            in returned tuples.
        PLAYER_STATA : for the list of messages corresponding to
            those status codes before they are localized.
        """

        for info in self._players:
            player = None if 2 > len(info) else info[1]
            if player is None:
                legend = 'expected'
            elif isinstance(player, RemoteEntity) and player.offline:
                legend = 'expected'
            else:
                legend = 'joined'
            code = (self.PLAYER_STATA_CODES[legend])
            yield (
                info[0],
                False if player is None or player.name is None else player.name,
                self.LOCALIZED_PLAYER_STATA[code],
                code
            )

    @property
    def ready(self):
        """
        Tell whether this object is ready to start a new game.

        A new game can be started when all players have joined
        and none of them is offline.

        See also
        --------
        playerStata : Provides information about each player's
            introduction status. 
        PLAYER_STATA_CODES : for explanation of status codes
            returned by the above method.
        """

        ready = True
        for status in self.playerStata:
            if status[3] == self.PLAYER_STATA_CODES['expected']:
                ready = False
                break
        return ready

    @property
    def tokens(self):
        """
        Immutable mapping of players' tokens to indexes of their
        seats at the table.

        The number of elements herein shall be the same as this
        object's `capacity`, and the set of its values shall
        be equal to ``set(range(object.capacity))``.
        """

        return mapping.ImmutableMap(self._tokens)

    _TOKEN_ALPHABET = 'abcdefghijklmnopqrstuvwxyz'
    

    @classmethod
    def createToken(clazz, length):
        """
        Create a random token to be assigned to a new player.

        Generates and returns a random token from characters in
        `_TOKEN_ALPHABET`.

        Parameters
        --------------------
        length : int
            A positive length of the token to be generated, in
            characters.

        Returns
        -------
        str
            The new random token or an empty string if `length`
            was zero or negative.

        Examples
        ----------------
        >>> len(PlayerCheckIn.createToken(5))
        5
        >>> len(PlayerCheckIn.createToken(1))
        1
        >>> PlayerCheckIn.createToken(1) in PlayerCheckIn._TOKEN_ALPHABET
        True
        >>> PlayerCheckIn.createToken(0)
        ''
        """
        token = ''
        range_ = len(clazz._TOKEN_ALPHABET)
        while 0 < length:
            token += clazz._TOKEN_ALPHABET[random.randrange(range_)]
            length -= 1
        return token

    @classmethod
    def modifyToken(clazz, token):
        """
        Modify a random token to avoid clashing with existing tokens.

        Shifts the contents of a token left and appends a random
        character from `_TOKEN_ALPHABET` to modify a new token that
        clashes with an existing one.

        Parameters
        --------------------
        token : str
            A token to be modified.

        Returns
        -------
        str
            The modified token of the same length or an empty string if
            the supplied token was empty.

        Examples
        ----------------
        >>> PlayerCheckIn.modifyToken('')
        ''
        >>> mod=PlayerCheckIn.modifyToken('test')
        >>> len(mod)
        4
        >>> mod[:3] == 'est'
        True
        """
        if 0 < len(token):
            token = token[1:]
            token += clazz._TOKEN_ALPHABET[random.randrange(
                    len(clazz._TOKEN_ALPHABET))]
        return token

    def createTokens(self, count, length = 5):
        """
        Creates multiple tokens that do not duplicate any tokens assigned
        to players.
        
        This method repeatedly calls `createToken` to yield a certain
        number of tokens that will not duplicate any tokens stored in this
        object. To prevent an infinite loop, it will compare the sum of
        `count` and the number of tokens already stored with half the number
        of all possible tokens and balk if `count` is too large.
        
        Parameters
        ----------
        count : int
            The number of tokens to be generated.
        length : int, optional
            Length of the tokens to be generated, in characters.
            Defaults to 5.
    
        Yields
        ------
        str
            Tokens that will not duplicate any existing tokens mapped by
            `FACILITIES`. Note that returned tokens will not duplicate
            each other if you store each of them there before fetching the
            next one. 
    
        Raises
        ------
        ValueError
            If `count` is negative, `length` is zero or negative, or the sum of
            `count` and the number of tokens stored in this object exceeds a
            half of possible combinations of `length` characters from
            `_TOKEN_ALPHABET`.
    
        Examples
        --------
        >>> from cards.durak import Game
        >>> PlayerCheckIn.FACILITIES.clear()
        >>> checkIn = PlayerCheckIn(Game)
        >>> tokens = [ token for token in checkIn.createTokens(100) ]
        >>> len(tokens)
        100
        >>> any( len(token) != 5 for token in tokens )
        False
        >>> [ token for token in checkIn.createTokens(1,1) ][0] \\
        ...  in PlayerCheckIn._TOKEN_ALPHABET
        True
        >>> [ token for token in checkIn.createTokens(0,1) ]
        []
        >>> [ token for token in checkIn.createTokens(1,0) ]
        Traceback (most recent call last):
        ...
        ValueError: Parameter `length` must be positive, got 0
        >>> [ token for token in checkIn.createTokens(-1,1) ]
        Traceback (most recent call last):
        ...
        ValueError: Parameter `count` must be a positive number less or equal to half of 26**1, got -1
        >>> [ token for token in checkIn.createTokens(14-len(PlayerCheckIn.FACILITIES),1) ] #doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Parameter `count` must be a positive number less or equal to half of 26**1, got ...
        >>> tokens = [ token for token in checkIn.createTokens(13-len(PlayerCheckIn.FACILITIES),1) ]
        >>> len(tokens)+len(PlayerCheckIn.FACILITIES)
        13
        >>> for token in tokens[0:7-len(PlayerCheckIn.FACILITIES)]:
        ...  if token not in checkIn._tokens:
        ...   checkIn._tokens[token] = None
        >>> moreTokens = (
        ...  [ token for token in checkIn.createTokens(6,1) ]
        ... )
        >>> [ token for token in moreTokens if token in checkIn._tokens ]
        []
        """

        if 0 >= length:
            raise ValueError("Parameter `length` must be positive, got %d"
                             % length)
        if 0 > count or not (
                0 <= count + len(self.FACILITIES)
                  <= len(self._TOKEN_ALPHABET) ** length // 2
            ):
            raise ValueError(
                ("Parameter `count` must be a positive number"
                 + " less or equal to half of %d**%d, got %d")
                % (len(self._TOKEN_ALPHABET), length, count)
            )
        while 0 < count:
            token = self.createToken(length)
            while token in self.FACILITIES or token in self._tokens:
                token = self.modifyToken(token) 
            yield token
            count -= 1        

class DropBox:
    """
    A receptacle for messages that must be processed in
    a sequence.
    
    Objects of this class are intended to serve as mix-ins or
    delegates for entities that accept messages from concurrent
    senders and process them in the order they were received.
    Messages are submitted via ``submitMessage`` method, either as
    `DropBox.Message` objects, or the deferred function/method calls.
    When this object is no longer needed, you should
    call the `discard` method to free up resources used
    by the message queue.
    
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

    Methods
    -------
    submitMessage(message)
    submitMessage(function, *args, **kwargs)
        Submit a message for the recipient.
    discard(timeout):
        Shut down delivery and dispose of the internal thread
        and objects used to dispatch messages.
    receiveResponse(self, message, response, exception):
        Override this method to process responses from
        the message recipient.
    [<name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errors that are non-obvious or have a large chance of getting raised.>
    ... ]

    See Also
    --------------
    DropBox.Message : Encapsulates messages processed herein.

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

    def submitMessage(self, messageOrFunction, *args, **kwargs):
        """
        Submit a message for the recipient.
        
        The message can be formatted a `DropBox.Message` object,
        or a function/method call with arguments.
        """

        if callable(messageOrFunction):
            messageOrFunction = self.Message(messageOrFunction, args, kwargs)
        elif not isinstance(messageOrFunction, self.Message):
            raise TypeError(
                'Unknown type of messageOrFunction argument: %s'
                % type(messageOrFunction).__name__
            )
        elif len(args) > 0 or len(kwargs) > 0:
            raise ValueError(
                'Cannot submit extra arguments with a message object'
            )

        with self._submitLock:
            if messageOrFunction.isShutdownRequest(): 
                self._acceptMessages = False
            elif not self._acceptMessages or self._delivery is None:
                raise RuntimeError(
                   'The recipient is not accepting messages at this time'
                )
            self._messages.put(messageOrFunction)

    def receiveResponse(self, message, response, exception):
        """
        Override this method to process responses from
        the message recipient.
        
        This method must not return a value or raise exceptions.
        Default implementation does nothing.

        Parameters
        ----------
        message : DropBox.Message
            The message to which this response is made.
        response : object
            Value returned by the message function, if any.
            ``None`` here means that the function returned
            ``None`` or that there was no result.
        exception : BaseException | NoneType
            The exception raised by the message function
            or ``None`` if there was no exception.
        """

        pass

    def discard(self, timeout=.5):
        """
        Shut down delivery and dispose of the internal thread
        and objects used to dispatch messages.
        
        Call this method to free up resources taken by this game when
        it is no longer needed. The call will close the queue for
        accepting actions from players.

        Parameters
        ----------
        timeout : int | float | str | NoneType
            The number of seconds, or fractions thereof, to wait for the
            dispatcher thread to stop, or ``None`` to wait indefinitely.
    
        Raises
        ------
        RuntimeError
            If the dispatcher thread fails to stop within the `timeout`.
        ValueError
            If `timeout` is negative or cannot be converted to
            a number.
    
        See Also
        --------    
        TODOdoc
    
        Examples
        --------
        TODOdoc
        """

        if timeout is not None:
            timeout = float(timeout)
            if 0 > timeout or not math.isfinite(timeout):
                raise ValueError(
                    'Thread disposal timeout %g must'
                    ' be a finite positive number or zero'
                    % timeout
                )
        if self._delivery is not None:
            self.submitMessage(self.Message.SHUTDOWN_REQUEST)
            if threading.current_thread() is not self._delivery:
                self._delivery.join(timeout)
                if self._delivery.is_alive():
                    raise RuntimeError(
                       'the dispatcher thread did not stop in %s seconds.'
                       % timeout
                    )
                    self._submitLock.release() # acquired by the _deliveryLoop() shutdown  
            self._delivery = None

    class Message:
        """
        Container of a message on the `DropBox` queue.
        
        Messages on a `DropBox` queue are function or method
        calls with arguments. Callers add messages to the
        queue, and the delivery loop executes them sequentially
        in a separate thread. 
        
        Constructor parameters of this class' instances are
        the same as their attributes listed below.
    
        Attributes
        -----------------
        function : object
            A callable object to invoke when delivering the
            message.
        args : collections.Sequence 
            Positional arguments to pass to the ``function``
            when delivering the message.
        kwargs : collections.Mapping
            Keyword arguments to pass to the ``function``
            when delivering the message.
    
        Methods
        ---------------
        isShutdownRequest()
            If this message is requesting the `DropBox`
            to end its operations.  
    
        Raises
        ----------
        TypeError
            If any of the arguments are of improper types.
        """

        def __init__(self, function, args, kwargs):
            if function is not None:
                if not callable(function):
                    raise TypeError('Argument `function` must be callable')
                if not isinstance(args, collections.Sequence):
                    raise TypeError('Argument `args` must be a Sequence')
                if not isinstance(kwargs, collections.Mapping):
                    raise TypeError('Argument `kwargs` must be a Mapping')
            self.function = function
            self.args = args
            self.kwargs = kwargs

        def __str__(self):
            return \
                'message "%s" with arguments %s, %s' % (
                    getattr(self.function, '__name__', '<unknown>'),
                    self.args,
                    self.kwargs
                )

        def isShutdownRequest(self):
            return self.function is None

        def _deliver(self):
            return self.function(*self.args, **self.kwargs)

    Message.SHUTDOWN_REQUEST = Message(None, None, None)

    def _deliveryLoop(self):
        while True:
            message = self._messages.get()
            if message.isShutdownRequest():
                if self._delivery is not None:
                    # request submitted from another thread - lock until joined
                    self._submitLock.acquire()
                self._messages.task_done()
                while not self._messages.empty():
                    self._messages.get(False)
                    self._messages.task_done()
                break
            else:
                response, exception = None, None
                try:
                    response = message._deliver()
                except:
                    exception = sys.exc_info()[1]
                self.receiveResponse(message, response, exception)
                self._messages.task_done()

    def __init__(self):
        self._submitLock = threading.Lock()
        self._messages = queue.Queue()
        self._acceptMessages = True
        self._delivery = threading.Thread(
            target=self._deliveryLoop,
            name=type(self).__name__
        )
        self._delivery.daemon = True
        self._delivery.start()

class WebGame(cards.durak.Game, DropBox):
    """
    Subclass of `cards.durak.Game` that can serve
    asynchronous web players.
    
    TODOdoc ... with a message queue that accepts asynchronous ...
    TODOdoc ... When the game is over and this object is
    no longer needed, you should call the `discard` method
    to free up resources used by the action queue.

    Parameters
    ----------
    playerFactory : function
        This parameter is passed to the superclass and
        should follow its specifications.
    uiDispatcher : comety.Dispatcher
        `comety` UI dispatcher for this game model. The model
        will use `comety` to send updates to web players.

    Attributes
    -----------------
    uiDispatcher
    [ <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    -------
    getPlayerClass(class_):
        Return the default type of objects that represent players in
        this game.
    discard(timeout):
        Delegates disposal request to the `DropBox`.
    [<name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

    Other parameters
    ----------------
    All other parameters are passed directly to the superclass's
    constructor.

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errorsself that are non-obvious or have a large chance of getting raised.>
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

    def __init__(self, playerFactory=None, uiDispatcher=None, **userSettings):
        super().__init__(playerFactory, **userSettings)
        DropBox.__init__(self)
        self._comety = uiDispatcher 

    PLAY_EVENT = 'play'
    GAME_OVER_EVENT = 'game-over'

    @classmethod
    def getPlayerClass(class_):
        """
        Return the default type of objects that represent players in
        this game.


        Returns
        -------
        type
            A subclass of `Player` objects that a concrete game creates
            to participate.
        """

        return WebPlayer

    def getUiDispatcher(self):
        """
        Return the `comety` UI dispatcher referenced by this object.

        The UI dispatcher associated with this object is used
        to send updates to web players when `receiveResponse`
        is called, or `WebPlayer` objects detect players' hand
        changes.

        Returns
        -------
        comety.Dispatcher
            The UI dispatcher associated with this object. The
            dispatcher is either passed to the constructor, or created
            lazily when this property is first
            read, and doesn't change.

        Examples
        --------
        TODOD: tests
        """

        if self._comety is None:
            self._comety = comety.Dispatcher()
        return self._comety

    uiDispatcher = property(getUiDispatcher)

    def receiveResponse(self, message, response, exception):
        """
        Process action responses from the game model and
        notify players of changes in the game.
        
        This method does not return a value.

        Parameters
        ----------
        message : DropBox.Message
            The message to which this response is made.
        response : object
            Value returned by the message function, if any.
            ``None`` here means that the function returned
            ``None`` or that there was no result.
        exception : BaseException | NoneType
            The exception raised by the message function
            or ``None`` if there was no exception.
        """

        if exception is None:
            try:
                target = message.args[0]
                cards_ = message.args[1] if 1 < len(message.args) else None
                eAttrs = {}
                if isinstance(target, cards.game.Player):
                    eAttrs['seat'] = target.seat
                if cards_ is not None:
                    eAttrs['attemptedCount']  = len(cards_)
                    eAttrs['accepted'] = response
                self.uiDispatcher.postEvent(self,
                    event = self.PLAY_EVENT,
                    move = message.function.__name__,
                    cardsOnTable = self.cardsOnTable(),
                    **eAttrs 
                )
            except:
                exception = sys.exc_info()[1]
        if exception is not None:
            log = logging.getLogger(type(self).__module__)
            log.error(
                '%s processing %s: %s',
                type(exception).__name__, message, exception
            )

    def gameOver(self, result):
        """
        Notify players when the game ends.
        
        This method must not return a value or raise exceptions.

        Parameters
        ----------
        result : (int, int) | None
            A tuple with the game winner's and loser's indexes, or
            ``None`` if there was a tie.
        """

        super().gameOver(result)
        self.uiDispatcher.postEvent(self, event = self.GAME_OVER_EVENT,
                                    result = result)

class RemoteEntity:
    """
    Mixin for browser-driven player classes that prevents
    lockouts of remote players.
    
    Create a browser-driven player class for a game by extending
    its generic player class and adding this type to the list
    of superclasses. Remember to call the constructor defined
    here when creating instances of your subclass. 

    Attributes
    -----------------
    offline : bool
        A flag that signals that a timeout has occured on this
        player's connection.

    See Also
    --------------
    WebPlayer : Default type of player objects that uses this
        mixin.

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
    """

    def __init__(self):
        self.offline = False

class WebPlayer(cards.durak.Player, RemoteEntity):
    """
    Default type of objects that represent players in `WebGame`.
    
    Extends the default player class with `RemoteEntity`
    mixin for browser-driven player classes and notifies
    to the remote player about received cards.

[    Attributes
    -----------------
    <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
    attemptMove(action, args):
        Attempt to submit action string and arguments that represent 
        a player's move as a message to the game model.

    Other parameters
    ----------------
    All parameters are passed directly to the superclass's
    constructor.

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errors that are non-obvious or have a large chance of getting raised.>
    ... ]

    See Also
    --------------
    RemoteEntity : Mixin to this class that prevents
        lockouts of remote players.

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
    """

    def __init__(self, *pos, **kw):
        super(type(self),self).__init__(*pos, **kw)
        RemoteEntity.__init__(self)

    def attemptMove(self, action, args = None):
        """
        Submit action string and arguments that represent 
        a player's move as a message to the game model.

        This method translates a player's action requested by
        the front end and attempts to submit it to the model's
        message queue for processing.

        This method does not return a value. If there is a
        problem with message submission, it raises an exception.

        Parameters
        ----------
        action : str
            The action string that describes this move on the
            front end.
        args : object, optional
            Python object (e.g. a collection) that contains the
            action's arguments, such as cards played. 
    
        Raises
        ------
        ValueError
            If the action string is inappropriate,
            not allowed for the player, or the arguments do not match
            the action.
        RuntimeError
            If this player's game object does not accept messages. 
    
        See Also
        --------    
        DropBox : Receives messages submitted to the game model.
    
    [   Examples
        --------
        <In the doctest format, illustrate how to use this method.>
         ]
        """

        game = self.game
        if not isinstance(game, DropBox):
            raise RuntimeError(
                "Game of %s cannot accept messages" % type(game)
            )
        messageInfo = None
        if 'play' == action:
            messageInfo = self.PLAY_MESSAGES.get(self.status)
        elif 'concede' == action:
            messageInfo = ( WebPlayer.quitTurn, (self,), {} )
        else:
            raise ValueError('Unknown action: %s' % action)
        if messageInfo is None:
            raise ValueError(
                'Action "%s" cannot be taken by %s player #%d'
                % (action, self.status, self.seat + 1)
            )
        message = list(messageInfo)
        try:
            i = 1
            while len(message) > i:
                if (callable(message[i])):
                    message[i] = message[i](self, args)
                i += 1
        except:
            raise ValueError(
                'Arguments %s are not valid for action "%s" by player #%d, %s'
                % (args, action, self.seat + 1, sys.exc_info()[0].__name__)
            ).with_traceback(sys.exc_info()[2])
        game.submitMessage(message[0], *message[1], **message[2])

WebPlayer.ATTACK_MESSAGE = ( WebPlayer.attack,
        lambda player, args: (player,
            tuple(cards.CardFace(code) for code in args)),
        {})

WebPlayer.PLAY_MESSAGES = {
        'attacking': WebPlayer.ATTACK_MESSAGE,
        'defending': ( WebPlayer.defend,
                      lambda player, args: (player,
                        dict((cards.CardFace(a), cards.CardFace(b))
                         for a,b in args.items())),
                      {}),
#        'collecting': None,
#        'quit': None,
        'other': WebPlayer.ATTACK_MESSAGE,
    }

if __name__ == "__main__":
    import doctest
    doctest.testmod()
