# vim:fileencoding=UTF-8 
################################
# Copyright © 2020 Stan Livitski
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
Pluggable authentication module (PAM) for the `cards_web` project
based on Django user authentication system.

TODO HOWTO configure

Key elements
------------
TODO 
"""

from cards_web.connect import Authenticator 
import version

version.requirePythonVersion(3, 4)

class BaseDjangoAuthenticator(Authenticator):
    """
    Authenticator that delegates to Django user authentication system.

    This authenticator works synchronously, but invokes the callback
    if one is provided. It does not accept arguments when constructed.
    """
    def __init__(self):
        self.userInfo = None

    def __call__(self, request, *args, callback_ = None, **kwargs):
        """
        Perform the authentication process.

        When called more than once, this method ignores the new request
        and other arguments, but notifies the new callback, if provided,
        and returns the status of prior authentication.
   
        Parameters
        ----------
        request : django.http.HttpRequest | NoneType
                Authentication request from a user, ignored
                on subsequent calls.
        callback_ : callable, optional
                The function or object to be notified of the
                authentication result. The two arguments that will be
                passed to the callback are the Django user record,
                or a boolean signaling authentication success, and the
                ``True`` on failure or ``None`` if the authentication
                succeeds.
    
        Other parameters
        ----------
        *args : tuple
            Ignored.
        **kwargs : dict
            Ignored.
   
        Returns
        -------
        django.contrib.auth.models.User | bool
            Django user record on success, or ``False`` on failure.
    
        Raises
        ------
        TypeError
            If the required arguments have an inappropriate type.

        Notes
        -----
        Returned user object may or may not have been authenticated
        by Django. In the latter case it will be an ``AnonymousUser``
        instance with ``is_authenticated`` property equal to ``False``.
    
        See Also
        --------    
        failure : Provides information about authentication failure, if any.
        """
        if self.userInfo is None:
            self.userInfo = request.user
        result = self.userInfo if self.userInfo else False
        if callback_ is not None:
            callback_(result, None if result else True)
        return result

class DjangoUserAuthenticator(BaseDjangoAuthenticator):
    """
    Authenticator that admits users recognized by the Django 
    authentication system as non-anonymous, or specific listed
    users.

    Parameters
    ----------
    *users : tuple(str)
        acceptable Django user names; all authenticated users
        are admitted if this argument is empty.
    """
 
    def __init__(self, *users):
        super().__init__()
        self.failure = None
        self.users = set(users)

    def __call__(self, request, *args, callback_ = None, **kwargs):
        result = super().__call__(request, *args, callback_ = None, **kwargs)
        if not result:
            return result
        elif self.failure is None:
            if not result.is_authenticated:
                self.failure = 'User not authenticated'
            elif self.users and result.username not in self.users:
                self.failure = 'User not listed as admissible'
        return False if self.failure else result

class DjangoGroupAuthenticator(BaseDjangoAuthenticator):
    """
    Authenticator that admits users belonging to specific Django 
    groups.

    Parameters
    ----------
    *groups : tuple(str)
        acceptable Django group names; at least one name
        must be present, but the actual groups don't have to exist
      
    Raises
    ------
    TypeError
        If there are no group arguments.
   """
 
    def __init__(self, *groups):
        super().__init__()
        self.failure = None
        if not groups:
            raise TypeError('No groups are listed in the configuration')
        self.groups = groups

    def __call__(self, request, *args, callback_ = None, **kwargs):
        result = super().__call__(request, *args, callback_ = None, **kwargs)
        if not result:
            return result
        elif self.failure is None and \
             not result.groups.filter(name__in = self.groups).exists():
            self.failure = 'User does not belong to group(s) ' \
                + ', '.join(self.groups)
        return False if self.failure else result
