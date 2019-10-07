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
    Classes that model the Durak game.
    
    <Extended description>

    Key elements
    ------------
    <python_name> : <One-line summary of a class, exception,
    function, or any other object exported by the module and
    named on this line.>
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
import abc
import math
import random
import collections
import os

import version
import mapping
import sets

import cards.game
from cards import CardFace

version.requirePythonVersion(3, 1)

class Game(cards.game.Game):
    """
    Implements a game of podkidnoy (throw-in) durak. 
    
    <Extended description>
    
    Parameters
    ----------
    lowestRank : int
        The lowest card rank in the deck played. Changing this
        will impact the maximum number of players allowed in the
        game, since the more cards are there in the deck, the
        more hands can be dealt. With the lowest rank of 6 (the
        default), the number of players admitted is 5.
    loserDefends : bool
        Whether or not the loser (fool) is the first defendant
        of the new game. Default is ``False``, meaning that the
        the first attacker in a new game seats on the loser's
        left.
    cardsPerHand : int
        The least number of cards that each player shall have on
        hand at the beginning of a turn until the talon is exhausted.
    playerFactory : function
        This and other parameters listed below are passed
        directly to the superclass and should follow its
        specifications. 
    players

[    <var>[, <var>] : <type | value-list>[, optional]
        <Description of constructor's parameter(s), except ``self``>
    ...]

    Attributes
    -----------------
    attacker : int | None
        Index of the first attacking player for the pending current turn
        or None if the attacking player has not yet been determined.
    defendant : int | None
        Index of the defending player for the pending or current turn
        or None if the defending player has not yet been determined.
    result : (int, int) | None
        A tuple with the last game winner's and loser's indexes, or
        ``None`` if no game had started yet or the last game was a tie.
        If there is a game in progress (see `playing`), the value of this
        property is unspecified.
    gamesPlayed : int
        The number of games played thus far.
    deckFactory : cards.DeckFactory
        An object that generates decks for this game.
    trumpCard : cards.CardFace
        The card at the bottom of stock that shows the trump suit.
    stockCount : int
        The number of cards remaining in stock, including the trump
        card.
    stats : collections.Sequence
        A sequence that accumulates win and loss counts by players
        in prior games. Elements are tuples with win and loss counts,
        in that order, for each player's seat.
    rankKeys : collections.Mapping
        Maps known card ranks to integer values for ordering
        within a suit. Jokers do not have a rank.
    playing
    lowestCardRank
    lowestCardRankRange
    playerCountRange
    cardsPerHand

    Methods
    ---------------
    cardsOnTable(self):
        Takes a snapshot of the cards played during the current turn.
    createDeckFactory(settings):
        Creates a factory object according to this game's configuration.
    rankKey(rank):
        Returns a numeric key for a card's rank.
    gameOver(self, result):
        Override this method to get notified when a game ends.
TODOdoc:
    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]

    Raises
    ----------
    Error
        If the game cannot be played with current settings, e.g. the
        number of players is too big for the deck.
    TypeError
        If any player objects supplied to, or generated for, this game
        are not instances of `Player` class.

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
    ----------------
    >>> def factory(game, playerNo):
    ...   return Player()
    >>> game = Game(factory)
    >>> game.settings['players']
    2
    >>> game.settings['lowestRank']
    6
    >>> len(game.players)
    2
    >>> game.gamesPlayed
    0
    """

    def __init__(self, playerFactory=None, **userSettings):
        super().__init__(playerFactory, **userSettings)
        self.deckFactory = self.createDeckFactory()
        self.defendant = None
        self.attacker = None
        self.result = None
        self.gamesPlayed = 0
        self._firstAttackClaims = None
        self._cardsOnTable = None
        playerCount = len(self.players)
        playerCountRange = self.playerCountRange
        if playerCountRange[0] > playerCount:
            raise Error(
                '%d player(s) is too few to start this game, need at least %d'
                % (playerCount, playerCountRange[0]))
        elif playerCountRange[1] < playerCount:
            raise Error(
                '%d player(s) is too many for deck size %d with %d cards per hand'
                % (playerCount, self.deckFactory.cardCount(), self.cardsPerHand))
        i = 1
        for player in self.players:
            if not isinstance(player, Player):
                raise TypeError('Player #%d must be a subtype of %s.%s, got: %s'
                    % (i, Player.__module__, Player.__name__, type(player))
                )
            i += 1
        self.stats = [ (0, 0) ] * playerCount

    @property
    def playing(self):
        """
        Flag telling whether a game is in progress at the moment.


        Returns
        -------
        boolean
            Whether a game is currently played.
    
    [   Examples
        --------
        <In the doctest format, illustrate how to use this method.>
         ]
        """

        return self.attacker is not None


    @classmethod
    def getPlayerClass(class_):
        """
        Return the base type of objects that represent players in
        this game.


        Returns
        -------
        type
            A subclass of `Player` objects that a concrete game creates
            or requires to participate.
        """

        return Player

    @cards.game.settingAccessor
    @staticmethod
    def getCardsPerHand(settings):
        """
        Read the effective value of the ``cardsPerHand`` setting.


        Returns
        -------
        int
            The least number of cards that each player shall have on
            hand at the beginning of a turn until the talon is exhausted.

        Examples
        ----------------
        >>> def factory(game, playerNo):
        ...   return Player()
        >>> game = Game(factory)
        >>> game.cardsPerHand
        6
        """
        return settings['cardsPerHand']

    cardsPerHand = property(getCardsPerHand)

    @cards.game.settingAccessor
    @staticmethod
    def getLowestCardRank(settings):
        """
        Read the effective value of the ``lowestRank`` setting.


        Returns
        -------
        str
            The lowest card rank that will be present on the game's
            deck.

        See Also
        --------
        cards.ranks: enumerates all known card ranks
        cards.SimpleDeckFactory: defines the range of accepted card rank values

        Examples
        ----------------
        >>> def factory(game, playerNo):
        ...   return Player()
        >>> game = Game(factory)
        >>> game.lowestCardRank
        '6'
        >>> game.lowestCardRank = 2
        >>> game.lowestCardRank
        '2'
        >>> game.lowestCardRank = '11'
        >>> game.lowestCardRank
        '11'
        >>> game.lowestCardRank = 1
        Traceback (most recent call last):
        ...
        ValueError: Unknown card rank: "1"
        >>> game.lowestCardRank = '12'
        Traceback (most recent call last):
        ...
        ValueError: Unknown card rank: "12"
        >>> game.lowestCardRank = 'queen'  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        ValueError: "queen"
        >>> settings = Game.defaults()
        >>> settings['players'] = 4
        >>> Game.getLowestCardRank(settings)
        '6'
        >>> Game.setLowestCardRank(settings, 8)
        >>> settings['lowestRank']
        8
        >>> Game.setLowestCardRank(settings, 9)
        Traceback (most recent call last):
        ...
        ValueError: A deck with lowest rank "9" is too small for 4 players when dealt 6 card(s) each
        """

        rank = str(settings['lowestRank'])
        assert rank in cards.CardFace.ranks_() or rank == '11'
        return rank

    @cards.game.settingAccessor
    def setLowestCardRank(self, settings, rank):
        """
        Change the value of the ``lowestRank`` setting.


        Parameters
        ----------
        rank : str
            The lowest card rank that will be present on the game's
            deck.

        Raises
        ----------
        TypeError
            If the game has already started and thus won't accept the
            change.
        ValueError
            If the game cannot be played with the new setting, e.g. the
            number of players is too big for the deck.
        """

        rank = str(rank)
        if not rank in cards.CardFace.ranks_() and not rank == '11':
            raise ValueError('Unknown card rank: "%s"' % rank)
        settings['lowestRank'] = int(rank)
        deckFactory = Game.createDeckFactory(settings)
        playerCount = len(settings['players']) \
            if isinstance(settings['players'], collections.abc.Sized) \
            else int(settings['players'])
        if deckFactory.cardCount() < 1 + settings['cardsPerHand'] * playerCount:
            raise ValueError('A deck with lowest rank "%s" is'
                ' too small for %d players when dealt %d card(s) each'
                % (rank, playerCount, settings['cardsPerHand']))
        if self is not None:
            self.deckFactory = deckFactory

    lowestCardRank = property(getLowestCardRank, setLowestCardRank)

    @cards.game.settingAccessor
    @staticmethod
    def getLowestCardRankRange(settings):
        """
        Read the range of possible lowest card ranks that may be
        present on the deck given the current player count.

        The minimum is a fixed value of ``2``, but may be
        different in subclasses. The maximum depends
        on the current player count, since a single deck
        must accommodate the number of hands to be dealt.

        Returns
        -------
        (int, int)
            The tuple of smallest and the largest
            rank of the lowest cars from the deck.
            Neither element may be negative, and the second
            element must not be smaller than the first.

        Examples
        ----------------
        >>> def factory(game, playerNo):
        ...   return Player()
        >>> game = Game(factory)
        >>> game.lowestCardRankRange
        (2, 11)
        >>> settings = Game.defaults()
        >>> settings['players'] = 8
        >>> Game.getLowestCardRankRange(settings)
        (2, 2)
        """

        suitCount = len(CardFace.suits_())
        playerCount = len(settings['players']) \
            if isinstance(settings['players'], collections.abc.Sized) \
            else int(settings['players'])
        dealCount = playerCount * Game.getCardsPerHand(settings) + 1
        return (2, 15 - int(math.ceil(dealCount / suitCount)))

    lowestCardRankRange = property(getLowestCardRankRange)

    @cards.game.settingAccessor
    @staticmethod
    def getPlayerCountRange(settings):
        """
        Read the range of possible player counts that apply when
        a game begins.

        The current minimum is a fixed value of ``2``, but may be
        converted to a setting in future, or in subclasses.
        The maximum depends on other settings, since a single deck
        must accommodate the number of hands to be dealt.

        Returns
        -------
        (int, int)
            The tuple of smallest number of players and the largest
            number of players that may be present when a game begins.
            Neither element may be negative, and the second
            element must not be smaller than the first. However,
            the second element may be ``None`` to indicate no upper
            limit on player count.  

        Examples
        ----------------
        >>> def factory(game, playerNo):
        ...   return Player()
        >>> game = Game(factory)
        >>> game.playerCountRange
        (2, 5)
        """

        deckFactory = Game.createDeckFactory(settings)
        max_ = (deckFactory.cardCount() - 1) // Game.getCardsPerHand(settings)
        return (2, max_)

    playerCountRange = property(getPlayerCountRange)

    @cards.game.settingAccessor
    @staticmethod
    def createDeckFactory(settings):
        """
        Create a factory object according to this game's configuration.


        Returns
        -------
        cards.DeckFactory
            A factory that may be used to create decks for this game's
            configuration.
        """
        return cards.SimpleDeckFactory(settings['lowestRank'], 0)

    # TODO: convert this into a setting
    defaultSuitOrder = ('spades', 'diamonds', 'clubs', 'hearts')

    @property
    def settings(self):
        settings = self._settings
        return settings if isinstance(settings, mapping.ImmutableMap) \
            else mapping.ImmutableMap(settings)

    @classmethod
    def defaults(class_):
        """
        Provide default values of settings specific to this game.

        This method adds default values of settings defined for
        `cards.durak.Game` class to the defaults returned by its parent
        method.
        
        See Also
        --------------
        cards.game.Game.defaults() : Parent method that sets
        requirements for its descendants.
        """
                
        defaults = super().defaults()
        defaults['cardsPerHand'] = 6
        defaults['lowestRank'] = 6
        defaults['loserDefends'] = False
        return defaults

    _rankKeys = {
        'ace': 14,
        'king': 13,
        'queen': 12,
        'jack': 11
    }
    _rankKeys.update((str(k), k) for k in range(2, 11))

    rankKeys = mapping.ImmutableMap(_rankKeys) # TODO: make me read-only
    del _rankKeys

    @staticmethod
    def rankKey(rank):
        """
        Return a numeric key for a card's rank.
        
        This method maps ranks of `cards.CardFace` objects
        to numeric values to order cards according to the
        Durak game rules. Jokers have no rank.
        
        Parameters
        ----------
        rank : str
            Rank of a card to be compared.

        Returns
        -------
        int
            Numeric value for the rank ordering.
    
        Raises
        ------
        ValueError
            If the rank string is invalid for this game,
            or the card is a joker.
    
        Examples
        --------
        >>> Game.rankKey('queen')
        12
        >>> Game.rankKey('10')
        10
        >>> Game.rankKey('6')
        6
        >>> Game.rankKey('joker')
        Traceback (most recent call last):
        ...
        ValueError: invalid rank of a card: joker
        >>> Game.rankKey('11')
        Traceback (most recent call last):
        ...
        ValueError: invalid rank of a card: 11
        >>> Game.rankKey('1')
        Traceback (most recent call last):
        ...
        ValueError: invalid rank of a card: 1
        >>> ranks=set(cards.CardFace.ranks_().keys())
        >>> ranks.discard('joker')
        >>> sorted(ranks, key=Game.rankKey)
        ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
        """
    
        if rank in Game.rankKeys:
            return Game.rankKeys[rank]
        else:
            raise ValueError('invalid rank of a card: %s' % rank)

    def start(self, dealer=None):
        """
        Establish initial state of a game in progress.
        
        This method establishes initial state of the game by freezing
        the settings that can't change during the game, dealing
        hands to players, pulling the trump card, preparing the
        stock, and setting up first turn. It can also be used to
        start a new game with the same players when the current game
        is over.

        Parameters
        ----------
        dealer : cards.Dealer, optional
            A dealer that will deal cards for this game. If omitted,
            a new `cards.Dealer` object with default settings will be
            created.

        Returns
        -------
        Game
            A reference to this object.
    
        Raises
        ------
        Error
            If the game has already been started.
        TypeError
            If ``deckFactory`` returns card objects of an unsupported
            type.
        ValueError
            If ``FIRSTATTACKER`` environment variable is not an integer
            or out of range.
    
        Examples
        --------
        >>> def factory(game, playerNo):
        ...   return Player()
        >>> game = Game(factory).start()
        >>> for player in game.players:
        ...   print('%s has cards: %s' % (player, player.hand)) #doctest: +ELLIPSIS
        player #0 has cards: (CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'))
        player #1 has cards: (CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'), CardFace('...'))
        >>> set(game.players[0].hand).isdisjoint(set(game.players[1].hand))
        True
        >>> dealt = set(game.players[0].hand) | set(game.players[1].hand)
        >>> dealt.isdisjoint(set(game._stock))
        True
        >>> game._stock[0] == game.trumpCard
        True
        >>> playerCount = game.settings['players']
        >>> playerCount == len(game.players)
        True
        >>> game.attacker < playerCount
        True
        >>> game.defendant < playerCount
        True
        >>> game.defendant != game.attacker
        True
        >>> game.playing
        True
        """
  
        if self.attacker is not None:
            raise Error(
                ('A game is in progress at bout #%d,'
                + ' cannot restart until it ends')
                % ( self._turn + 1 )
            )
        # Freeze the settings
        settings = self._settings
        if not isinstance(settings, mapping.ImmutableMap):
            self._settings = mapping.ImmutableMap(settings)
        if dealer is None:
            dealer = cards.Dealer()
        deck = dealer.shuffle(self.deckFactory.makeDeck(), 3)
        deal = dealer.deal(deck, len(self.players), self.cardsPerHand)
#        if os.environ.get('TESTHANDOVERFLOW'):
#            self._stock = deal[0][:1]
#            deal[-1].extend(deal[0][1:])
#            deal = ( self._stock, ) + deal[1:]
#        else:
        self._stock = deal[0] # The cards that haven't been dealt 
        # yet in the reverse order of their availability.
        self._stock.append(None)
        self._stock.reverse()
        last = self._stock.pop()
        self._stock[0] = last
        if not isinstance(last, cards.CardFace):
            raise TypeError(
                ('Cannot extract suit information from the trump card' +
                ', cards of type %s are not supported') % type(last))
        self.trumpCard = last
        self._cardsOnTable = collections.OrderedDict()
        self._discarded = set()
        self._turn = 0
        self._quits = set() 
        i = 1
        self._dealt = []
        for player in self.players:
            self._dealt.append(deal[i])
            player._receiveCards(tuple(deal[i]))
            i += 1
        self._cardsDefending = self.cardsPerHand
        index = os.environ.get('FIRSTATTACKER') 
        if index:
            index = int(index)
            if 0 <= index < len(self.players):
                self.attacker = index
            else:
                raise ValueError(
                    'FIRSTATTACKER %d is out of range (0, %d)'
                    % (index, len(self.players))
                )
        elif self.result is None:
            index = min(
                    self._firstAttackClaims, key =
                     lambda claim: Game.rankKey(claim[0])
                )[1] if self._firstAttackClaims else \
                    random.randrange(len(self.players))
            self.attacker = index
        elif self.settings['loserDefends']:
            # make the fool first defendant
            self.attacker = self.nextPlayersIndex(self.result[1], reverse = True)
        else:
            # by default the attacker is to the loser's left
            self.attacker = self.nextPlayersIndex(self.result[1])
        self.defendant = self.nextPlayersIndex(self.attacker)
        del self._dealt
        self._firstAttackClaims = None
        self.result = (None, None)
        return self

    def cardsOnTable(self):
        """
        Take a snapshot of the cards played during the current turn.
        
        Returns faces of the cards currently laying on the table, or
        an empty list if no cards have yet been played this turn.
    
        Returns
        -------
        list
            A list of tuples, each containing an attacking card and
            a respective defending card, if it is present. The order
            of tuples is the same that their attacking cards have
            been played.
    
        Raises
        ------
        RuntimeError
            If the game has not been started yet.
    
        See Also
        --------    
        Player : TODOdoc Examples section lists usage examples.
        """

        if self._cardsOnTable is None:
            raise RuntimeError("The game hasn't been started yet")
        return [ ( (item[0],) if item[1] is None else item ) \
                for item in self._cardsOnTable.items() ]

    def countPairsOnTable(self):
        """
        Return the number of card pairs played thus far during
        the current turn.
        
        
        Returns
        -------
        int
            The number of card pairs on the table at the moment.
    
        Raises
        ------
        RuntimeError
            If the game has not been started yet.
    
        Examples
        --------    
        TODOdoc
        """

        if self._cardsOnTable is None:
            raise RuntimeError("The game hasn't been started yet")
        return len(self._cardsOnTable)

    @property
    def stockCount(self):
        """
        Read-only property with the number of cards remaining in stock,
        including the trump card.


        Returns
        -------
        int
            The number of cards remaining.
    
        Raises
        ------
        AttributeError
            If this game has been started yet.
        """
        return len(self._stock)

    def nextPlayersIndex(self, index, reverse = False):
        """
        Increment and roll over a player's index to determine
        who defends against attack, who attacks next, etc.


        Parameters
        ----------
        index : int
            The index of the original player.
        reverse : bool, optional
            ``True`` to obtain an index of previous player instead
            of next. 

        Returns
        -------
        int
            The index of a player to the left of the original player.
        """
        
        index += -1 if reverse else 1
        if len(self.players) <= index:
            index = 0
        elif 0 > index:
            index = len(self.players) - 1
        return index

    def gameOver(self, result):
        """
        Override this method to get notified when a game ends.
        
        This method must not return a value or raise exceptions.
        Default implementation updates the `gamesPlayed` property.
        You should call it from overriding methods.

        Parameters
        ----------
        result : (int, int) | None
            A tuple with the game winner's and loser's indexes, or
            ``None`` if there was a tie.
        """

        self.gamesPlayed += 1

    def _claimFirstAttack(self, player, lowTrump):
        """
        Called by player objects receiving their cards when first game begins
        to determine which player moves first.
        
        According to the rules, the player with the lowest trump is the first
        attacker in the first game. In subsequent games, unless there was a
        draw, the first attacker is the player to the 
        right of the last game's loser (the fool). This
        method is called by players to claim their right to first attack. The
        implementation can verify the trump card presented by a player
        immediately, or defer verification until presented card is actually
        played. In the former case, this method shall throw an `Error`
        exception if the verification fails, and shall dishonor this claim
        of first attack.
        
        Parameters
        ----------
        player : Player
            A reference to the `Player` object that claims the first attack.
            This must be one of this game's players.
        lowTrump : object
            The lowest trump card from the claiming players' hand.
    
        Raises
        ------
        Error
            If this game object checked the claiming player's hand and did
            not find its presented card there, or the supplied player is
            not attached to this game.
        TypeError
            If this class does not support the type of card object
            presented.
        RuntimeError
            If this game is not ready for first attack claims and the trump
            suit is not yet known.
    
        See Also
        --------    
        attacker : If non-empty, the first mover is pre-determined
            and players should not call this method.
        """
    
        if not self.trumpCard:
            raise RuntimeError(
                'Unexpected call of _claimFirstAttack() before pulling the'
                + ' trump card')
        if self.attacker is not None or lowTrump.suit != self.trumpCard.suit:
            return
        index = self.players.index(player)
        if lowTrump not in self._dealt[index]:
            raise Error(
                'Card %s is not on the hand dealt to player #%d'
                % (lowTrump, index)
            )
        if self._firstAttackClaims is None:
            self._firstAttackClaims = [ ]
        self._firstAttackClaims.append((lowTrump.rank, index))

    def _isCardLimitReached(self):
        # cap the limit at the actual number of defenders' cards
        # in the beginning of a turn
        limit = min(self.cardsPerHand, self._cardsDefending) - (
             0 if self._turn else 1)
        return len(self._cardsOnTable) >= limit

    def _attack(self, player, cards_):
        """
        Attack the current defendant.
        
        Plays, or throws in, card(s) into the new or current attack.
        This method should only be called by the the attacking player
        object when that player is allowed to attack. The rules permit
        a player to attack when:
        
         - s/he is an attacker and the turn has just begun; or
         - s/he is not a defendant and joins the attack after it was
           launched, unless the limit of cards per attack has been
           reached or the turn has ended
        
        If the player has quit the turn by calling `_quitTurn`
        s/he is no longer allowed to attack until the next turn. 
        
        Parameters
        ----------
        player : Player
            Reference to the attacking player.
        cards_ : collections.Sized & collections.Iterable
            The cards to be played. If no cards have yet been played
            this turn, all cards must be of the same rank. Otherwise,
            each card's rank must coincide with any card that has
            been played this turn by any player.
    
        Returns
        -------
        collections.Sized & collections.Iterable & collections.Container
            The cards that have been played. When joining an attack,
            while other players are throwing cards in, the limit of
            cards for the turn may be met before all the offered
            cards are played. Thus, returned collection of cards
            may not be the same as the argument.  
    
        Raises
        ------
        Error
            If referenced player is not allowed to attack at this time,
            the cards played do not match ranks of cards on the table,
            or any of the cards have already been played.
        ValueError
            If referenced `Player` object is not attached to this game. 

        See Also
        --------    
        Player.attack : The method of `Player` class that calls this
            method. It should be the only place where this method is
            called. 
        """

        # check that this attack is appropriate
        playerIndex = self.players.index(player)
        if self.defendant is None or self.attacker is None:
            raise Error(
                'attack by %s cannot be started at this time' % player
            )
        elif self.defendant == playerIndex:
            raise Error(
                '%s is the defendant and cannot attack' % player
            )
        elif not self._cardsOnTable and playerIndex != self.attacker:   
            raise Error(
                '%s cannot attack at this time, waiting for %s'
                % (player, self.players[self.attacker]) 
            )
        elif playerIndex in self._quits:
            raise Error(
                '%s has quit the turn and cannot attack at this time'
                % player 
            )
        
        # check that correct cards are offered
        if not cards_:
            raise ValueError("attack() got an empty 'cards_' argument")
        elif self._cardsOnTable:
            for card in cards_:
                if not isinstance(card, cards.CardFace):
                    raise TypeError('received card of an unsupported %s' % type(cards_))
                if not (
                    any(card.rank == card2.rank for card2 in self._cardsOnTable.keys())
                    or
                    any(card.rank == card2.rank for card2 in self._cardsOnTable.values()
                        if card2 is not None)
                ):
                    raise Error(
                        "Rank of card '%s' does not match any of the cards on the table: %s"
                        % (card, self.cardsOnTable()) 
                    )
        else:
            cardIter = iter(cards_)
            card = next(cardIter)
            try:
                while True:
                    card2 = next(cardIter)
                    if card2.rank != card.rank:
                        raise Error(
                            "Rank of card '%s' does not match the first card played: '%s'"
                            % (card2, card) 
                        )
            except StopIteration:
                pass

        laid = set()
        for card in cards_:
            if self._isCardLimitReached():
                break
            if (card in self._cardsOnTable
             or card in self._cardsOnTable.values()
             or card in self._discarded
             or card in self._stock):
                for card2 in laid:
                    del self._cardsOnTable[card2]
                raise Error("card '%s' has already been played" % card.code)
            self._cardsOnTable[card] = None
            laid.add(card)
        if not self._stock and self.result[0] is None \
            and set(self.players[playerIndex].hand) == laid:
                # this player may have won
                self.result = (playerIndex, self.result[1])
        return laid

    def _defense(self, player, cardsMap):
        """
        Receive cards from the defending player.
        
        Called by the defending player to lay cards in its defense.
        Only the defending player object should call this method,
        supplying the defending cards as values of a map with cards
        they beat used as keys. Cards accepted for the defense are
        included in the return value. Note that this method may reject
        some cards without raising an exception.

        Parameters
        ----------
        player : Player
            Reference to the defending player.
        cardsMap : collections.Mapping
            A mapping of attacking cards on the table to the defendant's
            cards laid to beat them.
    
        Returns
        -------
        collections.Sized & collections.Iterable & collections.Container
            The defendant's cards that have been accepted. Cards from the
            argument with keys not present on the table or which already
            have been beat, or cards that won't beat its key card are not
            included in the result. The returned collection may be empty
            if no defending cards were accepted. 
    
        Raises
        ------
        Error
            If any of the defending cards have already been played or
            the player has abandoned the defense by calling `quitTurn`.
        ValueError
            If referenced `Player` object is not attached to this game. 
    
        See Also
        --------    
        Player.defend : The method of `Player` class that calls this
            method. It should be the only place where this method is
            called.
        """

        # check that this move is appropriate
        playerIndex = self.players.index(player)
        if self.defendant is None or self.attacker is None:
            raise Error(
                'defense by %s is not allowed at this time' % player
            )
        elif self.defendant != playerIndex:
            raise Error(
                '%s is not the defendant and cannot defend' % player
            )
        elif self.defendant in self._quits:
            raise Error(
                '%s has abandoned the defense' % player
            )
    
        laid = set()
        was = collections.OrderedDict(self._cardsOnTable)
        # check the cards laid
        for pair in cardsMap.items():
            card2 = pair[0]
            if (card2 not in self._cardsOnTable
             or self._cardsOnTable[card2] is not None):
                continue
            card = pair[1]
            if (card in self._cardsOnTable
             or card in self._cardsOnTable.values()
             or card in self._discarded
             or card in self._stock):
                self._cardsOnTable = was
                raise Error("card '%s' has already been played" % card.code)
            if card2.suit != card.suit:
                if self.trumpCard.suit != card.suit:
                    continue    # exclude non-trumps beating a different suit
                # trump card always beats non-trump
            elif self.rankKey(card.rank) <= self.rankKey(card2.rank):
                continue # exclude lower card beating the same suit
            self._cardsOnTable[card2] = card
            laid.add(card)
        return laid

    def _quitTurn(self, player):
        """
        Signal the end of turn for a specific player.
        
        Called by a player object to signal end of that player's participation
        in the current turn. This method determines whether the current turn
        should end according to the rules, and transitions the game into a new
        turn, or calls `gameOver` if the game has ended.
        
        Parameters
        ----------
        player
            Reference to the player that is calling this method.
    
        Raises
        ------
        ValueError
            If referenced `Player` object is not attached to this game.
        Error
            If the game hasn't been started, or no cards have been played
            in the current turn.
    
        See Also
        --------    
        Player.quitTurn : The method of `Player` class that calls this
            method. It should be the only place where this method is
            called.
        """
    
        playerIndex = self.players.index(player)
        unbeat = any( card is None for card in self._cardsOnTable.values() )
        oldDefendant, oldAttacker = self.defendant, self.attacker
        if oldDefendant is None or oldAttacker is None \
             or self._cardsOnTable is None:
            raise Error(
                '%s cannot quit the turn - no turn is in progress' % player
            )
        elif not self._cardsOnTable:
            raise Error(
                '%s cannot quit the turn - no cards have been played yet'
                % player
            )
        elif self.defendant != playerIndex:
            self._quits.add(playerIndex)
        elif unbeat:
            # allow others to throw in cards until the limit is reached
            self._quits.add(playerIndex)

        if unbeat and all(
              i in self._quits for i in range(0, len(self.players)) ):
            # abandoned defense - give the cards to ex-defendant
            defendant = self.players[self.defendant]
            for pair in self._cardsOnTable.items():
                defendant._receiveCards(pair[0])
                if pair[1] is not None:
                    defendant._receiveCards(pair[1])
            self._cardsOnTable.clear()
            self.attacker = self.nextPlayersIndex(self.defendant)
            self.defendant = None
        elif not unbeat and (
                self._isCardLimitReached() or all( i in self._quits
                for i in range(0, len(self.players)) if self.defendant != i )
            ):
            # end of turn, discard - all players quit, cards beaten
            for pair in self._cardsOnTable.items():
                assert pair[1] is not None
                self._discarded.update(pair)
            self._cardsOnTable.clear()
            self.attacker = self.defendant
            self.defendant = None

        # prepare next turn if the turn is over
        if self.defendant is None:               
            self._quits.clear()
            # deal cards to the former attacker first
            self._replaceCards(self.players[oldAttacker])
            # deal cards to the other contributors
            index = oldDefendant
            while oldAttacker != index:
                if index != oldDefendant:
                    self._replaceCards(self.players[index])
                index = self.nextPlayersIndex(index)
            # deal cards to the former defendant last
            self._replaceCards(self.players[oldDefendant])
            # a player can attack only if s/he has cards
            i = self.attacker
            while not self.players[i].hand:
                i = self.nextPlayersIndex(i)
                if i == self.attacker:
                    break
            if not self.players[i].hand:
                # game over, draw
                self.fool = self.attacker = None
                self.gameOver(None)
            else:
                self.attacker = i
                # a player can defend only if s/he has cards
                while True:
                    i = self.nextPlayersIndex(i)
                    if self.players[i].hand:
                        break           
                if self.attacker == i:
                    # game over, player #i lost
                    winner = self.result[0]
                    self.result = ( winner, i )
                    self.stats[i] = ( self.stats[i][0], 1 + self.stats[i][1])
                    self.stats[winner] = ( self.stats[winner][0] + 1,
                                           self.stats[winner][1])
                    self.attacker = None
                    self.gameOver(self.result)
                else:
                    self.defendant = i
                    self._cardsDefending = len(self.players[i].hand)
                    self._turn += 1

        if self.attacker is None:
            # end game
            del self._cardsDefending

    def _replaceCards(self, player):
        """
        Deal cards from the stock to a player that does not have
        the full hand.
        """
        
        hand = player.hand
        while self.cardsPerHand > len(hand) and self._stock:
            card = self._stock.pop()
            player._receiveCards(card)
        if not hand and self.result[0] is None:
            # this player may have won
            playerIndex = self.players.index(player)
            self.result = (playerIndex, self.result[1])

    # TODO: player notifications (provide notes for recursion avoidance)

class Player(cards.game.Player, metaclass=abc.ABCMeta):
    """
    Skeletal implementation of a durak game player.
    
    This class implements functions common to various kinds of durak
    players: interactive, robot, test, remote, validation, etc.
    This is an abstract class.

    Attributes
    -----------------
    hand
    STATUM
        Tuple containing possible values of the `status`
        property and logical conditions used to fill
        that property with one of those values.
[    <name_of_a_property_having_its_own_docstring> # or #
    <var>[, <var>] : <type | value-list>
        <Description of an attribute>
    ...]

    Methods
    ---------------
    attack(cards_):
        Attack the current defendant.
    defend(cardsMap):
        Defend the current turn.
    quitTurn():
        Request the end of the current turn for this player.
[TODOdoc:
    <name>([<param>, ...])
        <One-line description of a method to be emphasized among many others.>
    ...]
    
    Other parameters
    ------------------------------
    Any parameters to the constructor are passed to the superclass's
    constructor.

[    See Also
    --------------
    <python_name> : <Description of code referred by this line
    and how it is related to the documented code.>
    TODOdoc: built-in notification target
     ... ]

    Examples
    ----------------
    TODOtest: split this into localized examples, show important methods here
    TODOtest: move invalid calls to respective methods' doctests
    >>> from cards import CardFace
    >>> def factory(game, playerNo):
    ...   return Player()
    >>> class TestGame(Game):
    ...  def gameOver(self, result):
    ...   super().gameOver(result)
    ...   print("Game over, %s" % ('tie' if result is None
    ...    else '%d won, %d lost.' % result))
    >>> game = TestGame(factory, players = 2, lowestRank = 10)
    >>> game.settings['lowestRank']
    10
    >>> len(game.players)
    2
    >>> game.playing
    False
    >>> game.gamesPlayed
    0
    >>> class Dealer(cards.Dealer):
    ...  def shuffle(self, deck, times=1):
    ...   return [ deck ]
    ...  def deal(self, deck, handCount, cardsPerHand, cardsPerBatch=1, stockOffset=-1):
    ...   if 2 != handCount or 6 != cardsPerHand: raise NotImplementedError()
    ...   return ([ cards.CardFace(code) for code in ('AH','AS','AD','AC','10H','10S','10D','10C',) ],
    ...      [ cards.CardFace(code) for code in ('JH','JS','JC','JD','QC','QD') ],
    ...      [ cards.CardFace(code) for code in ('QH','QS','KS','KC','KH','KD') ],
    ...   )
    >>> game=game.start(Dealer())
    >>> game.playing
    True
    >>> game.trumpCard
    CardFace('AH')
    >>> game.attacker
    0
    >>> game.players[0].hand
    Hand(CardFace('JS'), CardFace('JD'), CardFace('QD'), CardFace('JC'), CardFace('QC'), CardFace('JH'))
    >>> game.players[0].status
    'attacking'
    >>> game.players[1].hand
    Hand(CardFace('QS'), CardFace('KS'), CardFace('KD'), CardFace('KC'), CardFace('QH'), CardFace('KH'))
    >>> game.players[1].status
    'defending'
    >>> game.players[1].attack([cards.CardFace('QS')])
    Traceback (most recent call last):
    ...
    Error: player #1 is the defendant and cannot attack
    >>> game.players[0].attack([cards.CardFace('QS')])
    Traceback (most recent call last):
    ...
    ValueError: player #0 does not have card 'QS' on her hand
    >>> game.players[0].attack([cards.CardFace('JS'),cards.CardFace('JH')]) \\
    ... == {cards.CardFace('JS'), cards.CardFace('JH')}
    True
    >>> game.players[0].attack([cards.CardFace('QD')])
    Traceback (most recent call last):
    ...
    Error: Rank of card 'QD' does not match any of the cards on the table: [(CardFace('JS'),), (CardFace('JH'),)]
    >>> game.players[0].hand
    Hand(CardFace('JD'), CardFace('QD'), CardFace('JC'), CardFace('QC'))
    >>> game.cardsOnTable()
    [(CardFace('JS'),), (CardFace('JH'),)]
    >>> game.players[1].defend({cards.CardFace('JH'): cards.CardFace('KC')})
    set()
    >>> game.players[1].defend({cards.CardFace('JS'): cards.CardFace('QH'), cards.CardFace('JH'): cards.CardFace('QH')})
    Traceback (most recent call last):
    ...
    Error: card 'QH' has already been played
    >>> game.cardsOnTable()
    [(CardFace('JS'),), (CardFace('JH'),)]
    >>> game.players[1].defend({cards.CardFace('JD'): cards.CardFace('KC'), cards.CardFace('JH'): cards.CardFace('QH')})
    {CardFace('QH')}
    >>> game.cardsOnTable()
    [(CardFace('JS'),), (CardFace('JH'), CardFace('QH'))]
    >>> game.players[1].defend({cards.CardFace('JS'): cards.CardFace('QS')})
    {CardFace('QS')}
    >>> game.cardsOnTable()
    [(CardFace('JS'), CardFace('QS')), (CardFace('JH'), CardFace('QH'))]
    >>> game.players[1].hand
    Hand(CardFace('KS'), CardFace('KD'), CardFace('KC'), CardFace('KH'))
    >>> game.players[1].defend({cards.CardFace('JC'): cards.CardFace('QS')})
    Traceback (most recent call last):
    ...
    ValueError: player #1 does not have card 'QS' on her hand
    >>> game.players[0].attack([cards.CardFace('QD'),cards.CardFace('QD')])
    Traceback (most recent call last):
    ...
    Error: card 'QD' has already been played
    >>> game.players[0].attack([cards.CardFace('QD')])
    {CardFace('QD')}
    >>> game.cardsOnTable()
    [(CardFace('JS'), CardFace('QS')), (CardFace('JH'), CardFace('QH')), (CardFace('QD'),)]
    >>> game.players[1].defend({cards.CardFace('QD'): cards.CardFace('KD')})
    {CardFace('KD')}
    >>> game.players[0].attack(
    ... [cards.CardFace('JD'),cards.CardFace('JC'),cards.CardFace('QC')]
    ... ) == {cards.CardFace('JC'), cards.CardFace('JD')}
    True
    >>> game.players[1].defend(
    ... {cards.CardFace('JD'): cards.CardFace('KH'),
    ...  cards.CardFace('JC'): cards.CardFace('KC')
    ... }).difference({CardFace('KC'), CardFace('KH')})
    set()
    >>> game.cardsOnTable()
    []
    >>> game.players[0].hand
    Hand(CardFace('10S'), CardFace('AS'), CardFace('AD'), CardFace('QC'), CardFace('AC'), CardFace('10H'))
    >>> game.players[1].hand
    Hand(CardFace('KS'), CardFace('10D'), CardFace('10C'), CardFace('AH'))
    >>> (game.attacker, game.defendant)
    (1, 0)
    >>> game.players[1].defend({})
    Traceback (most recent call last):
    ...
    Error: player #1 is not the defendant and cannot defend
    >>> game.players[1].attack((cards.CardFace('KS'), cards.CardFace('10D')))
    Traceback (most recent call last):
    ...
    Error: Rank of card '10D' does not match the first card played: 'KS'
    >>> game.players[1].attack((cards.CardFace('10C'), cards.CardFace('10D'))) \\
    ... == {CardFace('10D'), CardFace('10C')}
    True
    >>> game.cardsOnTable()
    [(CardFace('10C'),), (CardFace('10D'),)]
    >>> game.players[0].defend(
    ... {CardFace('10C'): CardFace('QC'), CardFace('10D'): CardFace('10H')}
    ... ) == {CardFace('10H'), CardFace('QC')}
    True
    >>> game.players[0].quitTurn()
    >>> game.cardsOnTable()
    [(CardFace('10C'), CardFace('QC')), (CardFace('10D'), CardFace('10H'))]
    >>> game.players[1].quitTurn()
    >>> game.cardsOnTable()
    []
    >>> (game.attacker, game.defendant)
    (0, 1)
    >>> game.players[0].hand
    Hand(CardFace('10S'), CardFace('AS'), CardFace('AD'), CardFace('AC'))
    >>> game.players[1].hand
    Hand(CardFace('KS'), CardFace('AH'))
    >>> game.players[0].attack([CardFace('AS'), CardFace('AD'), CardFace('AC')]) \\
    ... == {CardFace('AS'), CardFace('AD')}
    True
    >>> game.cardsOnTable()
    [(CardFace('AS'),), (CardFace('AD'),)]
    >>> game.players[1].quitTurn()
    >>> game.cardsOnTable()
    [(CardFace('AS'),), (CardFace('AD'),)]
    >>> game.players[0].attack([CardFace('AC')])
    set()
    >>> game.players[0].quitTurn()
    >>> game.cardsOnTable()
    []
    >>> (game.attacker, game.defendant)
    (0, 1)
    >>> game.players[0].hand
    Hand(CardFace('10S'), CardFace('AC'))
    >>> game.players[1].hand
    Hand(CardFace('KS'), CardFace('AS'), CardFace('AD'), CardFace('AH'))
    >>> game.players[0].attack([CardFace('10S')])
    {CardFace('10S')}
    >>> game.cardsOnTable()
    [(CardFace('10S'),)]
    >>> game.players[1].defend(
    ... {CardFace('10S'): CardFace('KS')})
    {CardFace('KS')}
    >>> game.players[0].quitTurn()
    >>> game.cardsOnTable()
    []
    >>> (game.attacker, game.defendant)
    (1, 0)
    >>> game.players[0].status
    'defending'
    >>> game.players[1].status
    'attacking'
    >>> game.playing
    True
    >>> game.players[0].hand
    Hand(CardFace('AC'),)
    >>> game.players[1].hand
    Hand(CardFace('AS'), CardFace('AD'), CardFace('AH'))
    >>> game.players[1].attack([CardFace('AS')])
    {CardFace('AS')}
    >>> game.players[0].quitTurn()
    >>> game.players[1].quitTurn()
    >>> game.cardsOnTable()
    []
    >>> game.players[0].hand
    Hand(CardFace('AS'), CardFace('AC'))
    >>> game.players[1].hand
    Hand(CardFace('AD'), CardFace('AH'))
    >>> (game.attacker, game.defendant)
    (1, 0)
    >>> game.players[1].attack([CardFace('AD')])
    {CardFace('AD')}
    >>> game.players[0].quitTurn()
    >>> game.players[0].status
    'collecting'
    >>> game.cardsOnTable()
    [(CardFace('AD'),)]
    >>> game.playing
    True
    >>> game.players[1].attack([CardFace('AH')])
    Game over, 1 won, 0 lost.
    {CardFace('AH')}
    >>> game.playing
    False
    >>> game.cardsOnTable()
    []
    >>> game.players[0].hand
    Hand(CardFace('AS'), CardFace('AD'), CardFace('AC'), CardFace('AH'))
    >>> game.players[1].hand
    Hand()
    >>> game.result
    (1, 0)
    >>> game.stats
    [(0, 1), (1, 0)]
    >>> game.gamesPlayed
    1
    """

    def __init__(self, *pos, **kw):
        super().__init__(*pos, **kw)
        self._hand = {} # a dictionary of sorted lists
        cardRank = lambda card: Game.rankKey(card.rank)
        for suit in cards.CardFace.suits_():
            self._hand[suit] = sets.SortedListSet(key = cardRank)  
        self.modCount = 0

    STATUM = (
        ('collecting', lambda game, index: game.defendant == index and index in game._quits),
        ('quit', lambda game, index: game.defendant != index and index in game._quits),
        ('attacking', lambda game, index: game.attacker == index),
        ('defending', lambda game, index: game.defendant == index),
        ('other', lambda game, index: True),
    )

    @property
    def status(self):
        """
        Read-only property that contains player's status in
        the current turn of the game.

        
        Returns
        -------
        str
            One of the `STATUM` values.

        Raises
        ------
        RuntimeError
            If this `Player` object is not attached to a game,
            or there is an internal problem with `STATUM` conditions. 
    
        See also
        --------
        Player : Examples section lists usage examples
        """
        
        if self.game is None:
            raise RuntimeError(
                'Cannot determine status of unattached player'
            )
        index = self.game.players.index(self)
        for status in self.STATUM:
            if status[1](self.game, index):
                return status[0]
        raise RuntimeError(
            'None of the STATUM conditions match %s' % self
        )

    @property
    def hand(self):
        """
        Read-only property that contains all cards currently held by this
        player.

        A sequence that contains all cards currently held by this player.
        The cards are arranged by suit in `Game.defaultSuitOrder`, then
        by rank in the order of `Game.rankKey`.
    
        Returns
        -------
        collections.Sequence
            A sequence of cards currently held by this player ordered
            alphabetically by suit, then by rank.
    
        Examples
        --------
        >>> player=Player()
        >>> player._receiveCards(cards.CardFace('6H'))
        >>> len(player.hand)
        1
        >>> cards.CardFace('6H') in player.hand
        True
        >>> cards.CardFace('AS') in player.hand
        False
        >>> player.hand
        Hand(CardFace('6H'),)
        >>> player._receiveCards([cards.CardFace('JS'),cards.CardFace('10C'),cards.CardFace('AD')])
        >>> len(player.hand)
        4
        >>> cards.CardFace('AS') in player.hand
        False
        >>> cards.CardFace('AD') in player.hand
        True
        >>> player.hand
        Hand(CardFace('JS'), CardFace('AD'), CardFace('10C'), CardFace('6H'))
        """
    
        return self.Hand(self, Game.defaultSuitOrder)

    @property
    def handBySuit(self):
        """
        Read-only property that contains all cards currently held by this
        player.

        A list that contains all cards currently held by this player grouped
        by suit. The items are tuples of suits that the player has on hand
        followed by lists of cards of each suit in the order of `Game.rankKey`.
    
        Returns
        -------
        collections.Mapping
            A mapping of suits of cards currently held by this player
            to lists of held cards of each suit ordered by rank.

        Examples
        --------
        TODO
        """

        handBySuit = []
        for suit in Game.defaultSuitOrder:
            cards = self._hand[suit]
            if cards:
                handBySuit.append((suit, list(cards)))
        return handBySuit


    @property
    def maxSuitLength(self):
        """
        Read-only property that contains the largest number of
        cards of the same suit currently held by this player.
    
        Returns
        -------
        int
            The largest number of cards of
            the same suit currently held by this player.
        """

        return max(len(cards) for cards in self._hand.values())
 
    def _receiveCards(self, cards_):
        """
        Receive one or more cards and add them to this player's hand.
        
        Called by the host `Game` to dispense cards dealt to, or
        accepted by, this player. Implementors SHOULD NOT call action
        methods such as `attack`, `defend`, or `quitTurn` from this
        method.
        
        Parameters
        ----------
        cards_ : collections.Iterable | CardFace  
            A source of objects, such as cards, to be added to this
            player's hand, or one such object.
    
        Returns
        -------
            The number of cards received.
    
        Raises
        ------
        TypeError
            If the type of an argument or any of its elements is unknown.
        Error
            If the player already has one of the cards offered.

    [   Examples
        --------
        <In the doctest format, illustrate how to use this method.>
         ]
        """
        
        if isinstance(cards_, collections.Iterable):
            for card in cards_:
                self._receiveCards(card)
            if self.game is not None and self.game.attacker is None:
                trumps = self._hand[self.game.trumpCard.suit]
                if trumps:
                    self.game._claimFirstAttack(self, next(iter(trumps)))
        elif isinstance(cards_, cards.CardFace):
            suit = self._hand[cards_.suit]
            if cards_ in suit:
                raise Error(
                    '%s already has card %s on its hand'
                    % ( self, cards_.code )
                )
            self.modCount += 1
            suit.add(cards_)
        else:
            raise TypeError('received card of an unsupported %s' % type(cards_))

    def attack(self, cards_):
        """
        Attack the current defendant.
        
        Launch an attack with selected cards from this player's hand.
        This method should only be called by the UI or AI that controls
        the player, and only when the player is allowed to attack. The
        rules permit a player to attack when:
        
         - s/he is an attacker and the turn has just begun; or
         - s/he is not a defendant and joins the attack after it was
           launched, unless the limit of cards per attack has been
           reached or the turn has ended
        
        The cards laid by calling this method are removed from the
        player's hand. 
        
        Parameters
        ----------
        cards_ : collections.Sized & collections.Iterable
            The cards to be played. If no cards have yet been played
            this turn, all cards must be of the same rank. Otherwise,
            each card's rank must coincide with any card that has
            been played this turn by any player.
    
        Returns
        -------
        collections.Sized & collections.Iterable & collections.Container
            The cards that have been played. When joining an attack,
            while other players are throwing cards in, the limit of
            cards for the turn may be met before all the offered
            cards are played. Thus, returned collection of cards
            may not be the same as the argument.  
    
        Raises
        ------
        Error
            If this player is not allowed to attack at this time,
            the cards played do not match ranks of cards on the table,
            or any of the cards have already been played.
        ValueError
            If this player does not have some of the cards from the
            argument on its hand.
        TypeError
            If this class does not support the type of card object
            presented.
        RuntimeError
            If this `Player` object is not attached to a game. 
    
        See also
        --------
        Player : Examples section lists usage examples.
        """
        
        if self.game is None:
            raise RuntimeError(
                'Attempt to act on behalf of unattached player')
        for card in cards_:
            if not isinstance(card, cards.CardFace):
                raise TypeError('trying to play card of an unsupported %s'
                % type(cards_))
            elif card not in self._hand[card.suit]:
                raise ValueError("%s does not have card '%s' on her hand"
                % (self, card))
        laid = self.game._attack(self, cards_)
        for card in laid:
            self.modCount += 1
            self._hand[card.suit].discard(card)
        # quit the attack when there are no more cards to play
        if not self.hand:
            self.game._quitTurn(self)
        return laid

    def defend(self, cardsMap):
        """
        Defend the current turn.
        
        Play cards to defend against the cards on table. This method
        should only be called by the UI or AI that controls the player,
        and only when the player is a defendant in the game. Defending
        cards are offered as values of a map with cards they beat used
        as keys. Cards accepted for the defense are included in the
        return value. Note that this method may reject some cards without
        raising an exception. The cards laid by calling this method are
        removed from the defendant's hand.

        When the defense beats all cards on the table, and the card
        limit for the turn has been reached or all other players have
        quit, this method calls `Game._quitTurn` to end the turn. 
        
        Parameters
        ----------
        cardsMap : collections.Mapping
            A mapping of attacking cards on the table to the defendant's
            cards laid to beat them.
    
        Returns
        -------
        collections.Sized & collections.Iterable & collections.Container
            The defendant's cards that have been accepted. Cards from the
            argument with keys not present on the table or which already
            have been beat, or cards that won't beat its key
            card are not included in the result. The returned collection
            may be empty if no defending cards were accepted. 
    
        Raises
        ------
        Error
            If any of the defending cards have already been played or
            the player has abandoned the defense by calling `quitTurn`.
        ValueError
            If this player does not have some of the cards from the
            argument on its hand.
        TypeError
            If this class does not support the type of card object
            presented.
        RuntimeError
            If this `Player` object is not attached to a game. 
    
        See also
        --------
        Player : Examples section lists usage examples.
        """

        game = self.game
        if game is None:
            raise RuntimeError(
                'Attempt to act on behalf of unattached player')
        for card in cardsMap.values():
            if not isinstance(card, cards.CardFace):
                raise TypeError('trying to play card of an unsupported %s'
                % type(card))
            elif card not in self._hand[card.suit]:
                raise ValueError("%s does not have card '%s' on her hand"
                % (self, card))
        laid = game._defense(self, cardsMap)
        for card in laid:
            self.modCount += 1
            self._hand[card.suit].discard(card)
        # end turn when there are no unbeaten cards and either:
        # -- the limit is reached, or
        # -- all other players quit
        # NOTE: defending cards must be removed from the player's hand first
        if (game._isCardLimitReached() or all( i in game._quits
                for i in range(len(game.players)) if i != game.defendant)) \
             and all(card is not None for card in game._cardsOnTable.values()):
            game._quitTurn(self)
        return laid

    def quitTurn(self):
        """
        Request the end of the current turn for this player.
        
        Called to signal the end of this player's participation
        in the current turn. When called on the defendant who hasn't beaten
        all the cards laid, this method results in an abandoned defense.
        Other players are then allowed to throw in cards with matching ranks
        until the card limit is reached or all players quit the turn.
        If all cards have been beaten, this method has no effect when called
        on the defendant, unless the number of cards has reached its limit
        for the turn. When the limit is reached, this method ends the turn.
        When called on a non-defending player, that player is no longer
        allowed to attack until the end of this turn. When all non-defending
        players have called this method and all cards have been beaten,
        the current turn ends regardless of the number of cards on the table.

        This method makes calls of `_receiveCards` on the game's players to
        complete an abandoned defense and dispense the stock cards to players
        who need them.
        
        Raises
        ------
        RuntimeError
            If this `Player` object is not attached to a game. 
        Error
            If the game hasn't been started, or no cards have been played
            in the current turn.

        See also
        --------
        Player : TODOdoc Examples section lists usage examples.
        """
    
        if self.game is None:
            raise RuntimeError(
                'Attempt to act on behalf of unattached player')
        self.game._quitTurn(self)

    class Hand(collections.Sized, collections.Iterable, collections.Container):

        def __init__(self, player, order):
            self._player = player       
            self._internal = player._hand
            self._order = order

        def __str__(self):
            return str(tuple(self))
    
        def __repr__(self):
            return type(self).__name__ + str(self)

        def __len__(self):
            return sum( len(self._internal[suit]) for suit in self._order ) 

        def __contains__(self, value):
            if not isinstance(value, cards.CardFace):
                raise TypeError(
                    ('Cannot extract suit information from card' +
                    ', cards of type %s are not supported') % type(value))
            return any( card == value for card in self._internal[value.suit] )

        def __iter__(self):
            return self.Iterator(self)

        class Iterator(collections.Iterator):
    
            def __init__(self, hand):       
                self._modCount = hand._player.modCount
                self._hand = hand
                self._suits = iter(hand._order)
                self._iter = None

            def __next__(self):
                if self._modCount != self._hand._player.modCount:
                    RuntimeError(
                        'hand of %s has been modified during the iteration'
                        % self._hand._player
                    )
                while True:
                    if self._iter is None:
                        self._iter = iter(self._hand._internal[next(self._suits)])
                    try:
                        return next(self._iter)
                    except StopIteration:
                        self._iter = None

class Error(Exception):
    """
    Signals an error within the game.
    
    Exceptions of this class are usually raised to signal an
    attempt to break the rules, such as playing the same card twice,
    attacking or defending against the rules, or ending the turn
    prematurely.
    
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

[   Examples
    ----------------
    <In the doctest format, illustrate how to use this class.>
     ]
    """

    pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
