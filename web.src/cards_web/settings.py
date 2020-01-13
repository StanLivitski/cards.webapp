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

import os
import warnings

from django.conf import global_settings as _global_settings

# Construct paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEPENDENCIES_DIR = os.path.join(BASE_DIR, 'depends')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'DJANGO_SECRET_KEY'
if SECRET_KEY in os.environ:
    SECRET_KEY = os.environ[SECRET_KEY]
else:
    warnings.warn('Please set the %s environment variable to a secret value'
                  ' shared by all the application\'s processes, or the startup'
                  ' may fail.' % SECRET_KEY)
    SECRET_KEY = _global_settings.SECRET_KEY

# TODO: SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [ '*' ]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('CARDS_WEB_LOG_LEVEL', 'INFO'),
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': None
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

SESSION_COOKIE_AGE = 10800

# Application definition
INSTALLED_APPS = (
    'durak_ws.Application',
    'comety.django',
# TODO: clean this up or use to maintain players' names/passwords
#    'django.contrib.admin',
    'django.contrib.auth', # required by Django 1.9+
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

# Monkey patch of django.contrib.staticfiles to allow browsers to cache them
#===============================================================================
# import django.contrib.staticfiles.views
# from django.utils.cache import patch_response_headers
# 
# _static_view_internal = None
# 
# def static_view(request, path, insecure=False, **kwargs):
#     response = _static_view_internal(request, path, insecure=insecure, **kwargs)
#     patch_response_headers(response)
#     return response
# 
# if _static_view_internal is None:
#     _static_view_internal = django.contrib.staticfiles.views.serve
#     django.contrib.staticfiles.views.serve = static_view
#===============================================================================
# End monkey patch of django.contrib.staticfiles

# TODO: clean this up
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# TODO: eliminate?
#WSGI_APPLICATION = 'cards_web.wsgi.application'


# Database

# TODO: get rid of this if our service doesn't use a database
#       otherwise, document (and script?) any database initialization
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

STATICFILES_DIRS = (
    ("scaler", os.path.join(DEPENDENCIES_DIR, 'scaler/src')),
)
