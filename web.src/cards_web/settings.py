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
"""
Django settings for cards_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import cards_web

import logging
import os
import stat
import sys
import warnings

from tempfile import mkdtemp
from urllib.parse import urlsplit

from django.conf import global_settings as _global_settings

# Scheme, location, and path URL parts to be prepended to the
# application's URLs before showing them to external clients.
# By default, the project is assumed to run
# on a local network, so no external URLs are formed.
# Otherwise, the value is a sequence of scheme, location, and path
# strings, or a URL string combined from these components.
EXTERNAL_URL_PREFIX = None

# The above value converted to a sequence, or ``None``
EXTERNAL_URL_PREFIX_ = ( urlsplit(EXTERNAL_URL_PREFIX, '', False)
            if isinstance(EXTERNAL_URL_PREFIX, str)
            else EXTERNAL_URL_PREFIX )

# Construct paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEPENDENCIES_DIR = os.path.join(BASE_DIR, 'depends')

# Target directory for app deployment files 
if 'CARDS_STAGING_DIR' in os.environ:
    STAGING_DIR = os.environ['CARDS_STAGING_DIR']
else:
    STAGING_DIR = os.getcwd()
if not os.path.samefile(STAGING_DIR, os.path.dirname(BASE_DIR)):
    STAGING_DIR = os.path.join(STAGING_DIR, os.path.basename(os.path.dirname(BASE_DIR)))

# Security

# WARNING: keep the secret key used in production secret!
SECRET_KEY = 'DJANGO_SECRET_KEY'
if SECRET_KEY in os.environ:
    SECRET_KEY = os.environ[SECRET_KEY]
else:
    warnings.warn('Please set the %s environment variable to a secret value'
                  ' shared by all the application\'s processes, or the startup'
                  ' may fail.' % SECRET_KEY)
    SECRET_KEY = _global_settings.SECRET_KEY

# This must be on to serve static files on a local network
# WARNING: turn this off and deploy static files to a web server when serving the Internet 
DEBUG = True
ALLOWED_HOSTS = [ '*' ]

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'handlers': ['console'],
        'level': os.getenv('CARDS_WEB_LOG_LEVEL', 'WARNING'),
    },
    'loggers': {
        'django': {
            'handlers': [],
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': logging.INFO if os.environ.get('CARDS_WEB_TRACE_FILE') else logging.CRITICAL,
            'propagate': False,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'cards_web',
        },
        'django.server': {
            'class': 'logging.FileHandler',
            'formatter': 'django.server',
            'filename': os.environ['CARDS_WEB_TRACE_FILE']
        } if os.environ.get('CARDS_WEB_TRACE_FILE') else {
            'class': 'logging.NullHandler'
        },
    },
    'formatters': {
        'cards_web': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(asctime)s %(levelname)s %(name)s] %(message)s',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s %(request)s] %(message)s',
        }
    },
}

# Sessions

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': None
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

SESSION_COOKIE_AGE = 10800

# Application components

# TODO: clean this up
INSTALLED_APPS = (
    'durak_ws.Application',
    'comety.django',
    'django.contrib.auth', # required by Django 1.9+
    'django.contrib.contenttypes',
    'django.contrib.sessions',
#    'django.contrib.messages',
    'django.contrib.staticfiles',
)

# TODO: clean this up
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'cards_web.urls'

# TODO: clean this up
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
#                'django.template.context_processors.debug',
                'django.template.context_processors.request',
#                'django.contrib.auth.context_processors.auth',
#                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

#WSGI_APPLICATION = 'cards_web.wsgi.application'

# Database

DB_DIR = os.path.expanduser('~')
if '~' == DB_DIR:
    raise RuntimeError("Current user's home directory is not defined")
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DB_DIR, cards_web.__name__ + '.sqlite3'),
    }
}


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = None # use the system timezone

USE_I18N = True

USE_L10N = True

USE_TZ = False

LOCALE_PATHS = ( 'locale', )

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'

if EXTERNAL_URL_PREFIX_ is not None:
    STATIC_URL = (EXTERNAL_URL_PREFIX_[2][:-1]
                  if EXTERNAL_URL_PREFIX_[2][-1:] == '/'
                  else EXTERNAL_URL_PREFIX_[2]
                  + STATIC_URL)

STATICFILES_DIRS = (
    ("scaler", os.path.join(DEPENDENCIES_DIR, 'scaler/src')),
)

if os.path.basename(sys.argv[0]).lower() == 'manage.py' and \
     1 < len(sys.argv) and sys.argv[1].lower() == 'collectstatic':
    os.makedirs(STAGING_DIR, exist_ok = True)
    STATIC_ROOT = mkdtemp(prefix='static-', dir=STAGING_DIR)
    os.chmod(STATIC_ROOT, stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)
