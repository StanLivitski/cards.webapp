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
    Modules that model items and actions involved in card games.
    
    The package module defines classes that implement playing cards
    and basic operations with them.

    Key elements
    ------------
    CardFace : A class that describes a playing card by its rank
    and suit.
    DeckFactory : A protocol for classes that create decks of
    cards.
    SimpleDeckFactory : Creates decks of standard (French) playing
    cards.
    Dealer : Shuffles and deals decks of cards.
    game : A module that provides skeletal classes to help model
    card games.
    durak : A module that models the Durak game.
    ... TODO: other modules, if any

[    See Also
    --------
    <python_name> : <Description of code named on this line
    and how it is related to the documented module.>
    ... ]

[    Examples
    --------
    <In the doctest format, illustrate how to use this module.>
]
"""

import abc
import collections
import random

import comety
import mapping
import version

version.requirePythonVersion(3, 3)

class CardFace(collections.Hashable, comety.JSONSerializable):
    """
    Describes a playing card by its rank and suit.
    
    Objects of this class contain immutable rank and suit
    information about a playing card. In addition, they provide
    equality and hashing operations for use of cards in data
    structures.
    
    Parameters
    --------------------
    rankSuitOrCode : str | (object, str)
        Specifies the identity of a card to create. The argument
        is either a string of the form '<rank-code><suit-code>'
        that identifies the new card; or a number or full name of
        a rank, and a full name of a suit.  

    Attributes
    -----------------
    code
    ranks
    suits
    rank : str
        A string from the set of `ranks` keys identifying the
        card's rank. 
    suit : str | None
        A string from the set of `suits` keys identifying the
        card's suit. For a joker (as determined by an `isJoker()`
        call, this may be a None, since jokers don't have a suit.
        Other cards are required to have a string value here. 

    Methods
    ---------------
    ranks_()
        Override this method in a subclass to define custom ranks for your
        cards.
    suits_()
        Override this method in a subclass to define custom suits for your
        cards.
    isJoker()
        Tell whether this card is a joker.

    Raises
    ----------
    TypeError
        If the constructor encounters invalid number or type of
        argument(s).
    ValueError
        If the constructor encounters invalid rank, suite, or code
        argument(s).

[    See Also
    --------------
    <python_name> : <Description of code referred by this line
    and how it is related to the documented code.>
    }

[    Notes
    ----------
    <Additional information about the code, possibly including
    a discussion of the algorithm. Follow it with a 'References'
    section if citing any references.>
    ]

    Examples
    ----------------
    >>> CardFace('3', 'hearts')
    CardFace('3H')
    >>> CardFace(7, 'clubs')
    CardFace('7C')
    >>> CardFace('joker', None)
    CardFace('*')
    >>> print(CardFace('QD'))
    QD
    >>> card=CardFace('AC')
    >>> print('%s of %s' % (card.rank, card.suit))
    ace of clubs
    >>> card=CardFace('10S')
    >>> print('%s of %s' % (card.rank, card.suit))
    10 of spades
    >>> CardFace(-177)
    Traceback (most recent call last):
    ...
    TypeError: Unsupported argument type: int
    >>> card=CardFace('10X')
    Traceback (most recent call last):
    ...
    ValueError: Unrecognized suit code: X
    >>> card=CardFace('21C')
    Traceback (most recent call last):
    ...
    ValueError: Unrecognized rank code: 21
    >>> card=CardFace('cub', 'clubs')
    Traceback (most recent call last):
    ...
    ValueError: Unrecognized rank 'cub'
    >>> card=CardFace('10', 'birds')
    Traceback (most recent call last):
    ...
    ValueError: Unrecognized suit 'birds'
    >>> CardFace(77, 'clubs')
    Traceback (most recent call last):
    ...
    ValueError: Unrecognized rank '77'
    """
    def _readOnlyAttr(self, name, *value):
        raise AttributeError(name + " is a read-only attribute")

    __setattr__ = _readOnlyAttr
    __delattr__ = _readOnlyAttr

    def __init__(self, *rankSuitOrCode):
        argc = len(rankSuitOrCode)
        if 1 == argc:
            rankSuitOrCode = rankSuitOrCode[0]
            if type(rankSuitOrCode) is not str:
                raise TypeError("Unsupported argument type: %s" % type(rankSuitOrCode).__name__)
            elif 0 == len(rankSuitOrCode):
                raise ValueError("Card code argument is empty")
            elif 1 < len(rankSuitOrCode):
                suitCode = rankSuitOrCode[-1:]
                suits = self.suits.reverse()
                if suitCode not in suits:
                    raise ValueError("Unrecognized suit code: " + suitCode)
                self.__dict__['suit'] = suits[suitCode]
                rankCode = rankSuitOrCode[:-1]
            else:
                rankCode = rankSuitOrCode
                self.__dict__['suit'] = None
            ranks = self.ranks.reverse()
            if rankCode not in ranks:
                raise ValueError("Unrecognized rank code: " + rankCode)
            self.__dict__['rank'] = ranks[rankCode]
            if self.suit is None and not self.isJoker():
                raise ValueError("Suit information missing from code: " + rankSuitOrCode)
        elif 2 == argc:
            if type(rankSuitOrCode[0]) is not str:
                rankSuitOrCode = (str(rankSuitOrCode[0]), rankSuitOrCode[1]) 
            self.__dict__['rank'], self.__dict__['suit'] = rankSuitOrCode
            if self.rank not in self.ranks:
                raise ValueError("Unrecognized rank '%s'" % self.rank)
            if self.suit is None:
                if not self.isJoker():
                    raise ValueError("Suit argument missing for card with rank '%s'" % self.rank)
            elif self.suit not in self.suits:
                raise ValueError("Unrecognized suit '%s'" % self.suit)
        else:
            raise TypeError("CardFace.__init__() takes 1 or 2 arguments (%d given)" % argc)

    def __eq__(self, other):
        """
        Tests another object for equality.

        To be equal to a card, another object must also
        be a `CardFace` with the same `rank` and `suit`.

        Examples
        ----------------
        >>> h5 = CardFace('5', 'hearts')
        >>> c8 = CardFace(8, 'clubs')
        >>> j = CardFace('*')
        >>> hq = CardFace('QH')
        >>> h5 == c8 or h5 == j or h5 == hq
        False
        >>> hq == c8 or hq == j
        False
        >>> j == c8
        False
        >>> CardFace('5H') == h5
        True
        >>> CardFace('8C') == c8
        True
        >>> CardFace('joker', None) == j
        True
        >>> CardFace('queen', 'hearts') == hq
        True
        >>> CardFace('queen', 'spades') == hq
        False
        """

        return  (isinstance(other, CardFace) 
                and other.rank == self.rank 
                and other.suit == self.suit
                )

    def __hash__(self):
        """
        Computes a hash code of the card.

        Hash codes of this type of objects are based on
        `rank` and `suit`. When both properties are equal
        in two objects, their hash codes are the same.

        See Also
        --------
        __eq__ : Tests another object for equality to a card.

        Examples
        ----------------
        >>> hash( CardFace('5', 'hearts'))
        -5827640750347260731
        >>> hash( CardFace(8, 'clubs'))
        6943784480238868857
        >>> hash( CardFace('*'))
        789663310554931641
        >>> hash( CardFace('QH'))
        -1449699717559581882
        """

        hash_ = hash(self.rank)
        hash_ -= hash_ << 5
        if self.suit is not None:
            hash_ -= hash(self.suit)
        return -hash_

    def _json_data_(self):
        """
        The JSON representation of a card is a ``dict``
        with its `code`, `rank`, and `suit` properties,
        and a `class` entry with this object's class name.
        """
    
        return {
            'class': type(self).__name__,
            'code': self.code,
            'rank': self.rank,
            'suit': self.suit
        }

    def __str__(self):
        """
        The string form of a card is its `code` property.
        """
    
        return self.code

    def __repr__(self):
        """
        The serialized form of a card is its constructor call
        with card code argument.
        """
    
        return "%s('%s')" % (
                type(self).__name__,
                self.code.replace("'", "\\'")
                )
    
    @property
    def code(self):
        """
        Read-only property that returns a card's code.

        The code is a string of the form '<rank-code><suit-code>',
        where both codes are taken from values of `ranks` and
        `suits` mappings.
        """

        code = self.ranks[self.rank]
        if self.suit is not None:
            code += self.suits[self.suit]
        return code

    def isJoker(self):
        """
        Tell whether this card is a joker.

        Override to apply special rules for determining
        whether a card is a joker, or to disable jokers.
        Default implementation compares the card's `rank`
        with the 'joker' literal.

        Returns
        -------
        bool
            `True` if the card is a joker, `False` otherwise.

        See Also
        --------------
        suit : Jokers do not have a suit, so with them `suit` property
        may have a `None` value.
                
        Examples
        --------
        >>> CardFace('joker', None).isJoker()
        True
        >>> CardFace('king', 'spades').isJoker()
        False
        >>> CardFace('2', 'hearts').isJoker()
        False
        >>> CardFace('JC').isJoker()
        False
        >>> CardFace('*').isJoker()
        True
        """
    
        return 'joker' == self.rank

    @staticmethod
    def ranks_():
        """
        Return possible ranks for this type of cards mapped to
        respective rank codes as a dictionary.
        
        Subclasses should override this method if they need to
        customize ranks of implemented cards. The rank codes
        must be unique.
        
        Returns
        -------
        dict
            A dictionary that maps ranks to rank codes
            { str: str, ... }. The dictionary should have 
            ranks as its keys, and codes the values.
        """
    
        ranks = {
            'ace': 'A',
            'king': 'K',
            'queen': 'Q',
            'jack': 'J',
            'joker': '*',
        }
        for num in range(2, 11):
            ranks[str(num)] = str(num)
        return ranks

    _ranks = None # TODO: make me read-only
    @property
    def ranks(self):
        """
        Read-only property that implements lazy call of the
        `ranks_` method and creates  an immutable
        `mapping.ReversibleMap` from it.
        """
        if type(self)._ranks is None:
            type(self)._ranks = mapping.ImmutableMap(
                 mapping.OneToOneMap(self.ranks_())
                 )
        return type(self)._ranks

    @staticmethod
    def suits_():
        """
        Return possible suits for this type of cards mapped to
        respective suit codes as a dictionary.
        
        Subclasses should override this method if they need to
        customize ranks of implemented cards. The suit codes
        must be unique and consist of a single character.
        
        Returns
        -------
        dict
            A dictionary that maps suits to suit codes
            { str: str, ... }. The dictionary should have 
            suits as its keys, and codes the values.
        """
    
        return dict(spades='S', clubs='C', diamonds='D', hearts='H')

    _suits = None # TODO: make me read-only
    @property
    def suits(self):
        """
        Read-only property that implements lazy call of the
        `suits_` method and creates an immutable
        `mapping.ReversibleMap` from it.
        """
        if type(self)._suits is None:
            type(self)._suits = mapping.ImmutableMap(
                 mapping.OneToOneMap(self.suits_())
                 )
        return type(self)._suits

class DeckFactory(collections.Iterable, metaclass=abc.ABCMeta):
    """
    A protocol for classes that create decks of cards.

    This abstract class declares methods for sizing and making
    decks of cards and provides adapter methods for compatibility
    with built-in `iter` function.

    Methods
    ---------------
    makeDeck
        Create a new deck of cards.
    cardCount
        Return the number of cards in a deck.
    """

    @abc.abstractmethod    
    def makeDeck(self):
        """
        Create a new deck of cards and return its contents one card at
        a time.
        
        New deck of cards is created according to implementor's
        rules and any supplied parameters. Cards are dealt to the
        caller by yielding until the deck is exhausted.
        
        Yields    
        -------
        CardFace
            A card from the new deck in an implementation-specific order.
        """
    
        raise NotImplemented()
        yield None

    @abc.abstractmethod    
    def cardCount(self):
        """
        Return the number of cards in a deck.
        
        Return the number of cards in new decks created according to
        implementor's rules and any supplied parameters, if known.
    
        Returns
        -------
        int | None | tuple | set
            The number of cards in new decks created according to
            implementor's rules and any supplied parameters, or
            `None` if that number cannot be known in advance. If the
            number of cards varies, implementors may choose to return
            a `tuple` of the form (min, max) to indicate a range, or
            a `set` with elements {c1, ..., cn} to indicate a 
            discrete set of possible counts. Callers that choose not
            to process `tuple` or `set` return values should treat them
            as if `None` was returned.
        """
    
        raise NotImplemented()

    def __iter__(self):
        return self.makeDeck()



class SimpleDeckFactory(DeckFactory):
    """
    Creates decks of standard (French) playing cards.
    
    Creates decks of French playing cards stripped of lower ranks
    if requested, with optional jokers.
    
    Parameters
    --------------------
    lowestRank : int, optional
        A positive number from 2 to 11 that indicates the lowest
        rank of suited cards to be included in each deck. The default
        is 2 for deuce. 11 means that only face cards will be included.
    jokers : int, optional
        The number of jokers to be added to each deck. The default
        is 2. This number can be 0 or more.

    Attributes
    -----------------
    suits
        A sequence of suits in each deck.
    ranks
        A sequence of ranks in each deck, jokers excluded.
    jokers
        The number of jokers in each deck.

    Methods
    ---------------
    makeDeck()
        Create a new deck and yield its cards one at a time. 

    Examples
    ----------------
    >>> factory=SimpleDeckFactory()
    >>> factory.jokers
    2
    >>> sorted(factory.suits)
    ['clubs', 'diamonds', 'hearts', 'spades']
    >>> sorted(factory.ranks)
    ['10', '2', '3', '4', '5', '6', '7', '8', '9', 'ace', 'jack', 'king', 'queen']
    >>> sorted(SimpleDeckFactory(7).ranks)
    ['10', '7', '8', '9', 'ace', 'jack', 'king', 'queen']
    >>> { card for card in factory.makeDeck() } == { 
    ...  CardFace("2S"), CardFace("3S"), CardFace("4S"), CardFace("5S"), CardFace("6S"), CardFace("7S"), CardFace("8S"), CardFace("9S"), CardFace("10S"), CardFace("JS"), CardFace("QS"), CardFace("KS"), CardFace("AS"), 
    ...  CardFace("2C"), CardFace("3C"), CardFace("4C"), CardFace("5C"), CardFace("6C"), CardFace("7C"), CardFace("8C"), CardFace("9C"), CardFace("10C"), CardFace("JC"), CardFace("QC"), CardFace("KC"), CardFace("AC"), 
    ...  CardFace("2D"), CardFace("3D"), CardFace("4D"), CardFace("5D"), CardFace("6D"), CardFace("7D"), CardFace("8D"), CardFace("9D"), CardFace("10D"), CardFace("JD"), CardFace("QD"), CardFace("KD"), CardFace("AD"), 
    ...  CardFace("2H"), CardFace("3H"), CardFace("4H"), CardFace("5H"), CardFace("6H"), CardFace("7H"), CardFace("8H"), CardFace("9H"), CardFace("10H"), CardFace("JH"), CardFace("QH"), CardFace("KH"), CardFace("AH"),
    ...  CardFace("*") # NOTE: this is a set, so there's just one joker here
    ... }
    True
    """

    def __init__(self, lowestRank = 2, jokers = 2):
        if not 2 <= lowestRank <= 11:
            raise ValueError(
                "Allowed values of lowestRank are 2 through 11, got: %s"
                % lowestRank
                )
        if 0 > jokers:
            raise ValueError(
                "Allowed values of jokers are positive, got: %s"
                % jokers
                )
        joker = CardFace('*') # create a joker to access attributes of CardFace
        self.__dict__['suits'] = tuple(joker.suits.keys())
        self.__dict__['ranks'] = tuple(
                rank for rank in joker.ranks
                 if joker.rank != rank and (not rank.isnumeric() or int(rank) >= lowestRank)
            )
        self.__dict__['jokers'] = jokers
 

    def makeDeck(self):
        """
        Create a new deck of cards and return its contents as required
        by `DeckFactory`.

        This method yields cards without any particular ordering. You
        have to sort or shuffle the cards you receive before playing the
        deck. 

        Yields    
        -------
        CardFace
            A card from the new deck in no particular order.
    
        Examples
        --------
        >>> deck = [ card for card in SimpleDeckFactory(6,0).makeDeck() ]
        >>> len(deck)
        36
        >>> CardFace('QC') in deck
        True
        >>> CardFace('6H') in deck
        True
        >>> CardFace('2H') in deck
        False
        >>> CardFace('*') in deck
        False
        """
    
        for suit in self.suits:
            for rank in self.ranks:
                yield CardFace(rank, suit)
        for rank in range(0, self.jokers):
            yield CardFace('joker', None)
        return

    def cardCount(self):
        """
        Return the number of cards in a deck.
        
        Return the number of cards in new decks created according to
        the parameters supplied to this object's constructor.
    
        Returns
        -------
        int
            The number of cards in new decks created by this factory.

        Examples
        --------
        >>> SimpleDeckFactory().cardCount()
        54
        """

        cards = len(self.suits) * len(self.ranks)
        return cards + self.jokers

class Dealer:
    """
    Shuffles and deals decks of cards.
    
    Each object of this class contains its own source of randomness,
    which is created and seeded by the constructor.
    
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
    ---------------
    shuffle(deck, times)
        Shuffle a collection (deck) of objects such as cards.
    deal(deck, handCount, cardsPerHand, cardsPerBatch, stockOffset)
        Deal hands from a collection of objects (deck of cards).

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errors that are non-obvious or have a large chance of getting raised.>
    ... ]

[    Notes
    ----------
    <Additional information about the code, possibly including
    a discussion of the algorithm. Follow it with a 'References'
    section if citing any references.>
    ]

    Examples
    ----------------
    >>> dealer = Dealer()
    >>> factory = SimpleDeckFactory(11,0)
    >>> deck = dealer.shuffle(factory,2)
    >>> len(deck)
    16
    >>> type(deck[0]) is CardFace
    True
    >>> deck[0].isJoker()
    False
    
    TODO: <In the doctest format, illustrate how to use this class.>
    """
    def __init__(self):
        self.random = random.Random()

    def shuffle(self, deck, times = 1):
        """
        Shuffle a collection (deck) of arbitrary objects, such as cards.
        
        This method shuffles a deck of objects (e.g cards) one or more
        times and returns the resulting sequence.
        
        Parameters
        ----------
        deck : DeckFactory | collections.Iterable
            A source of objects to shuffle.
        times : int, optional
            The number of times the deck is to be shuffled, must be
            positive.
    
        Returns
        -------
        collections.Sequence
            A sequence of shuffled objects from the supplied deck.

        Raises
        ----------
        TypeError
            If the `DeckFactory.cardCount()` method of a supplied `deck`
            object returns a value of incorrect type.
        IndexError
            If the `DeckFactory.cardCount()` method of a supplied `deck`
            object reports a count smaller than actual number of cards.
    
        Notes
        -----
        Cards are stored in a list, then shuffled by swapping all its
        elements in a linear sequence with random peers. This object's
        own source of randomness is used to determine the peers.
    
        Examples
        --------
        >>> dealer = Dealer()
        >>> result = dealer.shuffle([1,2,3], 3)
        >>> {1,2,3} == set(result)
        True
        >>> result = dealer.shuffle(range(0,52))
        >>> set(result) == set(range(0,52))
        True
        >>> result == [ i for i in range(0,52) ]
        False
        """
    
        if 0 >= times:
            raise ValueError("Value of 'times' must be positive, got: %d"
                % times)

        count = None
        if isinstance(deck, DeckFactory):
            count = deck.cardCount()
            if type(count) is int:
                pass
            elif isinstance(count, collections.Iterable):
                count = max(count)
            elif count is not None:
                raise TypeError("Unexpected type '%s' of the deck.cardCount() value: %s"
                                % (type(count).__name__, count))
             
        shuffled = [] if count is None else [ None ] * count
        i = 0
        if count is None:
            for card in deck:
                shuffled.append(card)
                i += 1
        else:
            for card in deck:
                shuffled[i] = card
                i += 1
        count = i
        while 0 < times:
            i = count
            while 0 < i:
                i -= 1
                other = self.random.randrange(count)
                shuffled[i],shuffled[other] = shuffled[other],shuffled[i]
            times -= 1 
        return shuffled

    def deal(self,
             deck,
             handCount,
             cardsPerHand,
             cardsPerBatch = 1,
             stockOffset = -1):
        """
        Deal hands from a collection of objects (deck of cards).
        
        Deals cards from a deck sequentially to a specified number of hands.
        Each hand receives a batch of cards at a time, then dealer deals to
        the next hand, and so on until the specified number of cards is dealt
        to each hand. Remaining cards are placed in the stock, which may
        begin or end at a specific offset in the initial deck.
        
        Parameters
        ----------
        deck : collections.Sequence
            A sequence of objects (such as cards) to be dealt.
            If `deck` is a `collections.MutableSequence`, all objects will
            be removed from it on success, otherwise the sequence will be
            copied into a new list before dealing.
        handCount : int
            The number of hands to be dealt, must be positive.
        cardsPerHand : int
            The number of cards to be dealt to each hand, must be positive.
        cardsPerBatch : int, optional
            The number of cards in a batch dealt to one hand before
            switching to the next one. Defaults to one.
        stockOffset : int, optional
            Offset of the stock of undealt cards (aka. talon, widow, skat,
            etc.) in the initial deck. This may be a positive number to locate
            the stock's first card relative to the beginning of the deck, or
            a negative number to point at the stock's **last card** relative
            to the end of the deck. Default value of -1 means that the stock's
            last card is the last card of the initial deck. The offset must
            be chosen to accommodate for the entire stock within the deck
            without rolling over its edges.
    
        Returns
        -------
        tuple
            Contains the stock at index 0 and the hands dealt at indexes
            equal to their numbers. Both stock and the hands are returned
            as lists.
    
        Raises
        ------
        ValueError
            If the cards cannot be dealt according to supplied parameters.
        TypeError
            If the deck object does not have a supported type.
    
        Examples
        --------
        >>> dealer = Dealer()
        >>> deck = dealer.shuffle( SimpleDeckFactory(7,0), 3)
        >>> prefCards = set(deck)
        >>> len(deck)
        32
        >>> hands = dealer.deal(deck, 3, 10, 2, -3) # Preferance deal
        >>> [ len(h) for h in hands ]
        [2, 10, 10, 10]
        >>> [ len(set(h)) for h in hands ]
        [2, 10, 10, 10]
        >>> len(deck)
        0
        >>> from functools import reduce 
        >>> # Merge hands and stock, make sure it's the same deck
        >>> prefCards==reduce(lambda a,b: a|set(b), hands, set()) 
        True
        >>> deck = dealer.shuffle( SimpleDeckFactory(6,0) )
        >>> len(deck)
        36
        >>> players = 2
        >>> hands = dealer.deal(list(deck), players, 6) # Durak deal
        >>> [ len(h) for h in hands ]
        [24, 6, 6]
        >>> # Merge hands and stock, make sure it's the same deck
        >>> set(deck)==reduce(lambda a,b: a|set(b), hands, set())
        True
        """
    
        if 0 >= handCount:
            raise ValueError("Argument 'handCount' must be positive, got: "
                             + str(handCount))
        if 0 >= cardsPerHand:
            raise ValueError("Argument 'cardsPerHand' must be positive, got: "
                             + str(cardsPerHand))
        if not 0 < cardsPerBatch <= cardsPerHand:
            raise ValueError(
                 "Argument 'cardsPerBatch' must be from 1 to %d, got: %d"
                 % (cardsPerHand, cardsPerBatch)
            )
        if not isinstance(deck, collections.Sequence):
            raise TypeError(
                 "Argument 'deck' does not have a collections.Sequence type: "
                 + type(deck).__name__
            )
        elif not isinstance(deck, collections.MutableSequence):
            deck = list(deck)
        cardsToDeal = handCount * cardsPerHand
        cardsInStock = len(deck) - cardsToDeal
        if 0 > cardsInStock:
            raise ValueError(
                 "Total number of cards to deal (%d) is larger than the deck (%d cards)"
                 % (cardsToDeal, len(deck))
            )
        elif 0 == cardsInStock:    
            stock = []
        elif 0 > stockOffset:
            from_ = stockOffset - cardsInStock + 1
            if -from_ > len(deck): 
                raise ValueError(
                     "Stock offset %s is insufficient to withhold %d cards from the deck of %d"
                     % (stockOffset, cardsInStock, len(deck))
                )
            to = stockOffset + 1
            if 0 == to: to = None
            stock = deck[from_ : to]
            del deck[from_ : to]
        else:
            to = cardsInStock + stockOffset
            if to > len(deck): 
                raise ValueError(
                     "Stock offset %s is insufficient to withhold %d cards from the deck of %d"
                     % (stockOffset, cardsInStock, len(deck))
                )
            stock = deck[stockOffset : to]
            del deck[stockOffset : to]
        hands = [ stock ]
        for i in range(0, handCount):
            hands.append([])
        deck.reverse() # reverse in place to allow dealing from the end
        i = 1
        while 0 < len(deck):
            hand = hands[i]
            batchSize = min(cardsPerBatch, cardsPerHand - len(hand))
            assert 0 < batchSize
            hand.extend(deck[-batchSize:])
            del deck[-batchSize:]
            i += 1
            if handCount < i: i = 1
        assert i == 1
        return tuple(hands)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
