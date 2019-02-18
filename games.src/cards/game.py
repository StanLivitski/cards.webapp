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
    Skeletal classes that help model card games.
    
    <Extended description>

    Key elements
    ------------
    Game : Abstract base class for card games.
    Player : Abstract base class for a card game player.

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
    players : int | collections.Iterable
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
    [ # or # <name_of_a_property_having_its_own_docstring>
    ...]

    Methods
    ---------------
    defaults()
        Override to return default settings for a game.
    start()
        Override to set up initial state of a game within this object.
    settingAccessor(callable)
        Decorator of a callable that fetches or computes values based on
        a game's `settings`. The callable should take a mapping with settings
        as its sole argument. The result is a method that substitutes the value
        of the `Game.settings` attribute to the wrapped callable for that
        argument when its value is a `Game` instance.
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

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
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
        self.settings = mapping.ImmutableMap(settings)
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
        dict
            A mapping of settings' names to default values.
        """

        return {
            'players' : 2,
        }

    @staticmethod    
    def settingAccessor(callable_):
        """
        Decorator of a callable that fetches or computes values based on
        a game's `settings`.
        
        The wrapped callable should take a mapping with a game's settings
        as its sole argument. The result is a method that substitutes the value
        of the `Game.settings` attribute for that argument when it receives
        a `Game` instance.
        
        Parameters
        ----------
        callable_ : object
            A callable object, such as a function or static method,
            that fetches or computes values based on a game's `settings`.
            Its sole argument should be a `collections.Mapping`.
    
        Returns
        -------
        function
            A method that can be used as settings-based property accessor
            here or in a subclass. Returned method will accept a `Game`
            or a `collections.Mapping` as its sole argument, and raise a
            `TypeError` when it receives something different
    
        Raises
        ------
        TypeError
            When the argument is not a callable object.
    
        Examples
        --------
        >>> @Game.settingAccessor
        ... def playerCount(settings):
        ...  return settings['players']
        >>> class TestGame(Game):
        ...  def start(self):
        ...   return self
        ...  def createPlayer(self, seat):
        ...   return Player()
        ...  @classmethod
        ...  def getPlayerClass(class_):
        ...   return Player
        >>> playerCount(TestGame())
        2
        >>> playerCount({'players' : 5})
        5
        >>> playerCount(None)
        Traceback (most recent call last):
        ...
        TypeError: A @settingAccessor cannot accept an argument of type NoneType
        """
        # A hack to dereference @staticmethod decorators 
        if not callable(callable_) and isinstance(callable_, staticmethod):
            callable_ = callable_.__func__
        if not callable(callable_):
            raise TypeError('Argument of type %s is not callable'
                            % type(callable_).__name__)
        def accessorFunction(selfOrSettings):
            if isinstance(selfOrSettings, Game):
                return callable_(selfOrSettings.settings)
            elif isinstance(selfOrSettings, collections.Mapping):
                return callable_(selfOrSettings)
            else:
                raise TypeError(
                    'A @settingAccessor cannot accept an argument of type %s'
                    % type(selfOrSettings).__name__)
        if '__name__' in dir(callable_):
            accessorFunction.__name__ = callable_.__name__
        if '__doc__' in dir(callable_):
            accessorFunction.__doc__ = callable_.__doc__
        return accessorFunction

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

#   @settingAccessor # use this decorator in implementations, cannot use here
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
[
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
[    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
]


    Returns
    -------
    <type | value-list>
        <Description of return value>
    ...

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
        # TODO: more

    def __str__(self):
        return (
            'new player' if self.game is None else 
            'player #%d' % self.seat
        ) + ( ': ' + self.name if self.name is not None else '' )

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

        if self.game is not None:
            raise AttributeError('Cannot change name of %s to %s'
                % (self, name))
        self._name = name

    name = property(getName, setName)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
