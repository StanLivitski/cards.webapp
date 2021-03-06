# vim:fileencoding=UTF-8 
#
# Copyright © 2015, 2016, 2017, 2019 Stan Livitski
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
    Skeletal classes that help model card games.
    
    <Extended description>

    Key elements
    ------------
    Game : Abstract base class for card games.
    Player : Abstract base class for a card game player.
    settingAccessor : Decorator of a callable that fetches or computes
        values based on a game's `settings`.

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
import abc
import collections
import mapping

from callables import prepare_call

def settingAccessor(globals_ = {}):
    """
    Decorator of a callable that fetches or computes values based on
    a game's `settings`.
    
    The wrapped callable should take a mapping with a game's settings
    as its first (or second, in case of non-static methods) argument.
    The result is a method that substitutes the value
    of the `Game.settings` attribute for that argument when it receives
    a `Game` instance. Decorated methods may also be called with
    `settings` as the binding object, in which case the method's
    code will receive ``None`` as the first argument. Accessors
    that gracefully handle such calls will be able to work on
    standalone `settings` objects.
    
    Parameters
    ----------
    globals_ : collections.Mapping
        The dictionary of the module defining the target callable,
        or the local dictionary for the scope in which the target callable's
        container is defined. If the container has not yet been defined
        (e.g. when processing a decorator) this mapping should also contain
        its future qualified name mapped to the ``object`` type value.
        This argument may be omitted when decorating static, class, and
        bound methods. 
    
    Other parameters
    ----------------
    callable_ : callable
        A callable object, such as a function or static method,
        that fetches or computes values based on a game's `settings`.
        Its sole argument should be a `collections.Mapping`.
        When the decorator is called without parentheses, this is
        its sole argument, and ``globals_`` is assumed to be empty.

    Returns
    -------
    function
        A method that can be used as settings-based property accessor
        here or in a subclass, or a decorator that produces such method.
        Resulting unbound method will accept a `Game`
        or a `collections.Mapping` as its sole argument, and raise a
        `TypeError` when it receives something different

    Raises
    ------
    TypeError
        When the argument is not a callable object.

    Examples
    --------
    >>> @settingAccessor(globals())
    ... def playerCount(settings):
    ...  return settings['players']
    >>> class TestGame(Game):
    ...  def start(self):
    ...   return self
    ...  @property
    ...  def playing(self):
    ...   return False
    ...  def createPlayer(self, seat):
    ...   return Player()
    ...  @classmethod
    ...  def getPlayerClass(class_):
    ...   return Player
    >>> game = TestGame()
    >>> playerCount(game)
    2
    >>> playerCount({'players' : 5})
    5
    >>> playerCount(None)
    Traceback (most recent call last):
    ...
    TypeError: A @settingAccessor cannot accept an argument of type NoneType
    """

    def with_globals(callable_):
        callable_, selfNeeded = prepare_call(callable_, globals_)
        if selfNeeded:
            def accessorFunction(selfOrSettings, *args, **kwargs):
                if isinstance(selfOrSettings, Game):
                    return callable_(selfOrSettings, selfOrSettings._settings, *args, **kwargs)
                elif isinstance(selfOrSettings, collections.Mapping):
                    return callable_(None, selfOrSettings, *args, **kwargs)
                else:
                    raise TypeError(
                        'A @settingAccessor cannot accept an argument of type %s'
                        % type(selfOrSettings).__name__)
        else:
            def accessorFunction(selfOrSettings, *args, **kwargs):
                if isinstance(selfOrSettings, Game):
                    return callable_(selfOrSettings._settings, *args, **kwargs)
                elif isinstance(selfOrSettings, collections.Mapping):
                    return callable_(selfOrSettings, *args, **kwargs)
                else:
                    raise TypeError(
                        'A @settingAccessor cannot accept an argument of type %s'
                        % type(selfOrSettings).__name__)
        if '__name__' in dir(callable_):
            accessorFunction.__name__ = callable_.__name__
        if '__doc__' in dir(callable_):
            accessorFunction.__doc__ = callable_.__doc__
        return accessorFunction
    if isinstance(globals_, collections.Mapping):
        return with_globals
    else:
        target = globals_
        globals_ = {}
        return with_globals(target)
        

class Game(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for card games.
    
    TODO: Extended description
    
    The constructor takes as arguments settings, such as number of
    players, rule tweaks, scoring conventions, etc. Names and exact
    meanings of those settings depend on the concrete game. The game
    implementation should also provide defaults for settings that it
    does not receive explicitly. Settings that apply to the base
    class, and their default meanings, are listed below. To override
    a setting, supply a respective named parameter to the constructor.
    The constructor also takes care of creating actual `Player` objects
    if they are not supplied by a caller. See description of the
    `playerFactory` parameter below for details. 
    
    Parameters
    ----------
    playerFactory : function
        A function that generates player objects for this game.
        This function will be called with parameters (game, seat),
        where seat is the player's seat number starting from 0
        to 1 less than the `players` setting. If the `players` setting
        supplies all player objects to this game, this argument is ignored
        and may be omitted. As an alternative to supplying this function,
        you may override the `createPlayer` method in a subclass.
    players : int | collections.Collection
        The number of players in this game or a source of new
        `Player` objects to be attached to it. When this value is a
        number, or any of the values it yields is `None`, the
        `playerFactory` parameter or `createPlayer` method
        is used to obtain any missing players for the game. Otherwise,
        the players are obtained from the iterator. The
        default initial value of this setting is number 2.

    Attributes
    ----------
    settings : mapping.ImmutableMap
        Effective values of this game's settings supplied via its
        constructor or `defaults`().
    players : collections.Sequence
        A list of players in this game.
    playing
    [ # or # <name_of_a_property_having_its_own_docstring>
    ...]

    Methods
    ---------------
    defaults()
        Override to return default settings for a game.
    start()
        Override to set up initial state of a game within this object.
    playing() : boolean
        Override to tell whether a game is in progress at the moment.
[    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
]

    Raises
    ----------
    TypeError
        if any `players` objects or an object created by `playerFactory`
        callback or `createPlayer` method is not of the `Player` type.
    ValueError
        if iterator over `players` setting returns no elements
[    <exception_type>
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

    Examples
    --------
    >>> class TestGame(Game):
    ...  def start(self):
    ...   return self
    ...  @property
    ...  def playing(self):
    ...   return False
    ...  def createPlayer(self, seat):
    ...   return Player()
    ...  @classmethod
    ...  def getPlayerClass(class_):
    ...   return Player
    >>> game = TestGame(players = 5)
    >>> str(game)
    'TestGame with 5 player(s)'
    >>> game.players[0].game == game
    True
    >>> game.players[0] is game.players[0]._detachFromGame()
    True
    >>> game.players[0].game is None
    True
    """

    def __init__(self, playerFactory = None, **userSettings):
        settings = dict(self.defaults())
        settings.update(userSettings)
        # Create players and update the 'players' setting if necessary
        players = settings['players']
        self.players = None
        self.playerFactory = playerFactory
        playerClass = self.getPlayerClass()
        assert issubclass(playerClass, Player)
        if isinstance(players, collections.Iterable):
            self.players = [ player for player in players ]
            if not self.players:
                raise ValueError('Iterable `players` returned no elements')
            for seat in range(0, len(self.players)):
                if self.players[seat] is None:
                    self.players[seat] = self.createPlayer(seat)
                if not isinstance(self.players[seat], playerClass):
                    raise TypeError(
                        'Player object at seat %d is not derived from class %s: %s of %s'
                        % (
                            seat,
                            playerClass, self.players[seat],
                            type(self.players[seat])
                        )
                    )
            settings['players'] = len(self.players)
        else:
            self.players = [ None ] * players
            for seat in range(0, players):
                player = self.createPlayer(seat)
                if not isinstance(player, playerClass):
                    raise TypeError(
                        '%s returned an object not derived from class %s: %s of %s'
                        % (
                            ('createPlayer() in %s' % type(self) if playerFactory is None
                             else 'factory function %s' % playerFactory.__name__),
                            playerClass, player,
                            type(player)
                        )
                    )
                self.players[seat] = player
        # Make settings immutable
        self._settings = mapping.ImmutableMap(settings)
        # Check player objects and attach them to the game
        seat = 0
        for player in self.players:
            if not isinstance(player, Player):
                raise TypeError(
                    'Player object at seat %d is not derived from class Player: %s of %s' % (
                        seat,
                        player,
                        type(player)
                    )
                )
            player.game = self
            seat += 1
        del self.playerFactory
        # TODO: more initialization work

    def playAgain(self, *args, **kwargs):
        """
        Create a new game using this object as a template.

        This method creates a new game object and copies its
        settings and players from this one, except for those
        overwritten by the arguments or supplied by ``playerFactory``.
        The arguments should follow the pattern defined for
        the constructor. Superclasses adding or changing constructor
        arguments should override this method and handle similar
        arguments here as well. References to the copied player
        objects are retained herein, as it is presumed that
        this object is no longer used and will soon be discarded.
        """

        if 'playerFactory' in kwargs:
            playerFactory = kwargs.pop('playerFactory')
        elif 0 < len(args):
            playerFactory = args[0]
            args = args[1:]
        else:
            playerFactory = lambda game, seat: None
        def factory(game, seat):
            nonlocal self, playerFactory
            player = playerFactory(game, seat)
            if player is None:
                player = self.players[seat]
            return player
        settings = dict(self.settings)
        settings.update(kwargs)
        for player in self.players:
            player._detachFromGame()
        newGame = type(self)(playerFactory = factory, *args, **settings)
        return newGame

    def createPlayer(self, seat):
        """
        Override this method to generate player objects for new instances
        of a game.
        
        This method will be called for each player's seat in the game
        when `players` setting is an integer or yields a `None` value.
        Default implementation delegates to `playerFactory` if it is
        present, otherwise it returns `None` causing an exception in the
        game's constructor.
           
        Parameters
        --------------------
        seat : int
            player's seat number from a range of 0 to 1 less than the
            `players` setting or the number of elements it yields
    
        Returns
        -------
        Player
            a player object that will fill the seat specified by `seat`. 

        See Also
        --------------
        getPlayerClass : Tells the base type of objects that represent
            players in this game. Returned objects, if any, must be instances
            of that class.
        """
        return self.getPlayerClass()() if self.playerFactory is None \
                else self.playerFactory(self, seat)

    def __str__(self):
        """
        A string with game type and the number of players.
        """
    
        return "%s with %d player(s)" % (
            type(self).__name__, len(self.players) )

    @property
    def settings(self):
        return self._settings

    @classmethod
    def defaults(class_):
        """
        Override to return default settings for a game.
            
        This method is called to determine default settings of a
        new game object. Returned defaults take effect for settings
        not explicitly passed to the constructor. Base implementation
        returns a mutable dictionary with default values described
        for the `Game` constructor's arguments. Generally, you should
        call the superclass's implementation and add or change defaults
        for game-specific settings to the mapping it returns.    

        Returns
        -------           
        abc.mapping
            A mapping of settings' names to default values.
        """

        return {
            'players' : 2,
        }

    @classmethod
    @abc.abstractmethod
    def getPlayerClass(class_):
        """
        Override to return the base type of objects that represent
        players in this game.


        Returns
        -------
        type
            A subclass of `Player` objects that a concrete game creates
            or requires to participate.
        """

        raise NotImplementedError()

    @settingAccessor
    @staticmethod
    @abc.abstractmethod
    def getPlayerCountRange(settings):
        """
        Override to retrun the range of possible player counts that
        apply when a game begins.


        Returns
        -------
        (int, int)
            The tuple of smallest number of players and the largest
            number of players that may be present when a game begins.
            Neither element may be negative, and the second
            element must not be smaller than the first. However,
            the second element may be ``None`` to indicate no upper
            limit on player count.  
        """

        raise NotImplementedError()

    @abc.abstractmethod
    def start(self):
        """
        Override this method to set up initial state of a game.
        
        This method is called by the application when it starts
        a new game. After constructing a `Game`, the application
        may perform additional setup, such as injecting dependencies.
        When done with the setup, the application will call this
        method to start the game. The implementation should do things
        that bring the game to its initial state, such as dealing
        hands to players. Subclasses must be able to do that at least
        once in an object's lifetime. Subclasses may allow the
        application to restart the game by calling this method
        again, but are not required to do so.

        Returns
        -------
        Game
            A reference to this object.
    
        Raises
        ------
        Exception
            When this object is not configured correctly to start a
            game, or the game has already been started and cannot be
            restarted. 
        """
    
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def playing(self):
        """
        Flag telling whether a game is in progress at the moment.

        Override this method to report a game is in progress.
        Default implementation returns ``False``.

        Returns
        -------
        boolean
            Whether a game is currently played.
        """

        return False

    def gameOver(self, result):
        """
        Call this method to notify a subclass when a game ends.
        Override it to get notified when a game ends.
        
        This method must not return a value or raise exceptions.
        Default implementation does nothing.

        Parameters
        ----------
        result : object | None
            A value of unspecified type, or ``None``, that conveys
            the game's result.
        """

        pass


class Player:
    """
    Base class for a card game player.

    Provides functions that connect a game to its players. This is a
    class that defines an interface between a game and a player
    and implements methods shared by most player implementations.

[    Parameters
    --------------------
    <var>[, <var>] : <type | value-list>[, optional]
        <Description of constructor's parameter(s), except ``self``>
    ...]

    Attributes
    -----------------
    name
    game
    gamesPlayed
[
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
[    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
]


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

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
    """

    def __init__(self):       
        self._game = None
        self._name = None
        self._gamesPlayed = 0
        # TODO: more

    def __str__(self):
        return (
            'new player' if self.game is None else 
            'player #%d' % self.seat
        ) + ( ': ' + self.name if self.name is not None else '' )

    def _detachFromGame(self):
        """
        Clear the host `Game` object reference.

        This method should only be called by the host `Game`
        or its successor that also clears or updates inverse
        ``Player`` reference.

        Returns
        -------
        Player
            this object after it's detached

        Raises
        ------
        RuntimeError
            when an attempt is made to detach player from a
            `Game` in progress

        See Also
        --------------
        Game.playing : property of the game object disallowing
            this operation when set
        """

        if self._game is not None and self._game.playing:
            raise RuntimeError(
                'Attempt to detach %s from active %s' %
                 (self, self._game))
        self._game = None
        return self

    def attachToGame(self, game):
        """
        Inject a reference to the host `Game` object.
        
        This method is called by the `Game` object when it creates
        or receives `Player` instances to take seats in the game.
        It should not be called directly. Once a `Game` reference is
        assigned, it cannot be changed.
        
        Parameters
        ----------
        game : Game
            a reference to the host `Game` object
       
        Raises
        ------
        RuntimeError
            when an attempt is made to attach this object to a `Game`
            different from its current `Game` 
        """

        if self._game is not None and game is not self._game:
            raise RuntimeError(
                'Attempt to attach %s to a different %s' % (self, game))
        self._game = game

    def getGame(self):
        """
        Reference the host `Game` object.
        

        Returns
        -------
        Game | None
            Reference to the `Game` this player participates in, or
            `None` if this player has not yet been placed in the game.
        """
    
        return self._game

    game = property(getGame, attachToGame)

    @property
    def gamesPlayed(self):
        """
        Count of games played by this player.
        

        Returns
        -------
        int
            The number of games played by this player.
        """

        return self._gamesPlayed

    def _incrGamesPlayed(self):
        """
        Increment the number of games played by this player.
        """

        self._gamesPlayed += 1

    @property
    def seat(self):
        """
        Return the player's seat number starting from 0.
        
        Raises
        ------
        AttributeError
            if this player is not (yet) attached to a `Game` 
        """

        if self.game is None:
            raise AttributeError('This player is not in a game yet.')
        return self.game.players.index(self)

    def getName(self):
        """
        This player's name.
        

        Returns
        -------
        str | None
            The name given to this player or `None` if this player has
            not yet been given a name.
        """
    
        return self._name

    def setName(self, name):
        """
        Record the name of the player represented by this object.
        
        The player's name should be configured before this object
        is placed in a game. Once a `Game` reference is assigned,
        the player's name cannot be changed.
        
        Parameters
        ----------
        game : Game
            a reference to the host `Game` object
       
        Raises
        ------
        AttributeError
            when an attempt is made to change the name of a
            player attached to a `Game` 
        """

        if self.game and self.game.playing:
            raise AttributeError(
                'Cannot change name from %s to %s while playing'
                % (self, name))
        self._name = name

    name = property(getName, setName)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
