# vim:fileencoding=UTF-8 
#
# Copyright © 2016, 2020 Stan Livitski
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
    Common code used by the game apps to set up
    connections with users and other nodes.
    

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

import netifaces

import abc
import collections
import socket

class Authenticator(abc.ABC):
    """
    Interface to an object that implements the user
    authentication function within game apps.
    
    A Pluggable Authentication Module (PAM) should
    provide a class of objects implementing this interface,
    or an equivalent function. Such authenticator is then
    referenced by the configuration file and created/called
    by an app to authenticate its user(s). Authentication
    may happen either synchronously or asynchronously,
    and PAMs must list all the authentication method(s)
    that they implement. An application does not have to
    support both synchronous and asynchronous authentication,
    and if it doesn't, it cannot be used with PAMs that don't
    implement a compatible method.

    If the callback is present and the PAM doesn't implement
    asynchronous authentication, it shall ignore the callback
    and assume the state that corresponds to the authentication
    result. If the callback is absent and the PAM implements
    only asynchronous authentication, it shall raise an exception
    listed below.

    A PAM that provides authenticator function instead of a class
    must have it accept the same arguments as the class constructor
    and return a `userInfo` value on success, ``False`` on failure,
    or ``None`` for asynchronous authentication in progress.

    Parameters
    ----------
    request : django.http.HttpRequest
            Authentication request from a user.
    callback_ : callable, optional
            If the application supports asynchronous authentication,
            it passes the function or object that will receive the
            authentication result. The two arguments that will be
            passed to the callback are the `userInfo` return value,
            or a boolean signaling authentication success, and the
            `failure` return value, or ``None`` if the authentication
            succeeds. *NOTE:* the callback may, but
            doesn't have to, be run on a different thread, outside
            the context of initial authentication request.

    Other parameters
    ----------
    args : tuple
        Positional arguments the application receives with the
        authentication request.
    kwargs : dict
        Keyword arguments the application receives with the
        authentication request.

    Raises
    ------
    TypeError
        If any of the above arguments has an inappropriate type,
        or the PAM supports only asynchronous authentication and
        no ``callback`` has been passed.
    """

    @abc.abstractmethod
    def __init__(self, request, *args, callback_ = None, **kwargs):
        """
        Create an authenticator and perform, or start, the
        authentication process.

        Notes
        -----
        See above for implementors' requirements.
        """

    @abc.abstractmethod
    def __bool__(self):
        """
        Indicate authentication success to the caller.
    
        Returns
        -------
        boolean
            ``True`` on success, ``False`` on failure.
    
        Raises
        ------
        TypeError
            When the authenticator has an asynchronous operation
            in progress.
    
        See Also
        --------    
        ready : Tells whether there is an asynchronous operation
            in progress without raising an error.
        """

    def ready(self):
        """
        Tell whether there is an asynchronous operation
        in progress with this authenticator.
        
        This method is optional. Asynchronous authenticators
        should implement it to report operations in progress
        without the expense of error handling.
    
        Returns
        -------
        boolean
            ``False`` if this authenticator is performing
            an asynchronous operation, ``True`` otherwise.
    
        See Also
        --------    
        userInfo : Provides information about the authenticated user
            if this method returns ``True``.
    
        Notes
        -----
        Default implementation casts this object to a boolean
        and returns ``True`` if that doesn't cause an error,
        or ``False`` otherwise.
        """
        try:
            bool(self)
            return True
        except:
            return False

    def userInfo(self):
        """
        Provides information about the authenticated user.
        
        This method is optional and any records it may return
        are implementation-specific.
    
        Returns
        -------
        object | bool
            A record describing the authenticated user, or ``True``
            with minimal implementations. This _must not_ evaluate
            to a ``False`` boolean value.
    
        Raises
        ------
        TypeError
            When the authenticator has an asynchronous operation
            in progress.
        RuntimeError
            If the authentication had failed.
    
        See Also
        --------    
        ready : Tells whether there is an asynchronous operation
            in progress without raising an error.
    
        Notes
        -----
        Default implementation casts this object to a boolean
        and returns the result, if it indicated success,
        raises `RuntimeError` on failure, or propagates any error
        raised.
        """
        if self:
            return True
        else:
            raise RuntimeError('Authentication failed')


    def failure(self):
        """
        Provides information about authentication failure, if any.
        
        This method is optional and its return values
        are implementation-specific.
    
        Returns
        -------
        object | string | bool
            A record or string explaining the authentication failure,
            or ``True`` returned by minimal implementations. This
            _must not_ evaluate to a ``False`` boolean value.
    
        Raises
        ------
        TypeError
            When the authenticator has an asynchronous operation
            in progress.
        RuntimeError
            If the authentication had succeeded.
    
        See Also
        --------    
        ready : Tells whether there is an asynchronous operation
            in progress without raising an error.
    
        Notes
        -----
        Default implementation casts this object to a boolean
        and returns ``True``, if it indicated failure, raises
        `RuntimeError` if the authentication succeeded, or propagates
        any error raised.
        """
        if not self:
            return True
        else:
            raise RuntimeError('Authentication succeeded')

def local_client_authenticator(request, *args, callback_ = None, **kwargs):
    """
    Authenticator function that admits local clients and provides no
    further user info.

    This authenticator works synchronously, but invokes the callback,
    if one is provided.
    
    Parameters
    --------------------
    request : django.http.HttpRequest
            Authentication request from a user.
    callback_ : callable, optional
            If the application supports asynchronous authentication,
            it passes the function or object that will receive the
            authentication result. The two arguments that will be
            passed to the callback are: a boolean signaling authentication
            success; and ``True`` to indicate failure, or ``None`` otherwise.

    Returns
    -------
    boolean
        Authentication status: ``True`` on success, ``False`` on failure,

    Other parameters
    ----------
    args : tuple
        Positional arguments received with the
        authentication request are ignored here.
    kwargs : dict
        Keyword arguments received with the
        authentication request are ignored here.

[    Raises
    ----------
    <exception_type>
        <Description of an error that the constructor may raise and under what conditions.
        List only errors that are non-obvious or have a large chance of getting raised.>
    ... ]

    See Also
    --------
    InboundAddressEnumerator : Compiles a list of client addresses
        that are considered local.
    """

    addrIsLocal = False
    for localInfo in InboundAddressEnumerator.resolve(type_ = socket.SOCK_STREAM):
        if (localInfo[1] in (socket.AF_INET, socket.AF_INET6) # family
             and localInfo[2] == request.META['REMOTE_ADDR']):
            addrIsLocal = True
            break
    if callback_ is not None:
        callback_(addrIsLocal, None if addrIsLocal else True)
    return addrIsLocal

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
