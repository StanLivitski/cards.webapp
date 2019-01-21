..
   Copyright 2015-2019 Stan Livitski
   
   Licensed under the Apache License, Version 2.0 with modifications
   and the "Commons Clause" Condition, (the "License"); you may not
   use this file except in compliance with the License. You may obtain
   a copy of the License at
   
    https://raw.githubusercontent.com/StanLivitski/cards.webapp/master/LICENSE
   
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


===============
 cards.webapp
===============

Web application for multiplayer card games. Self-hostable now,
federated in the future.

------------------
Installation guide
------------------

.. _prereqs-runtime:

Runtime prerequisites
=====================

To run this application, you need the following software installed
on your device:

.. raw:: html

 <style type="text/css"><!--
  td { padding: 0; }
  td a { font-size: small; }
 --></style>


+---------------------------------------------------+----------+
| Name / Download URL                               | Version  |
+===================================================+==========+
|| Python                                           || 3.2.3   |
|| https://www.python.org/downloads/                || or newer|
+---------------------------------------------------+----------+
|| setuptools                                       |matching  |
|| https://pypi.python.org/pypi/setuptools/         |the above |
|                                                   |Python    |
|                                                   |version   |
+---------------------------------------------------+----------+
|| Django                                           || 1.8.7   |
|| https://www.djangoproject.com/download/          || or newer|
+---------------------------------------------------+----------+
|| netifaces [#]_                                   |0.8       |
|| https://pypi.python.org/pypi/netifaces/          |          |
+---------------------------------------------------+----------+

.. template row
   |                                                   |          |
   |                                                   |          |
   +---------------------------------------------------+----------+
   
.. [#] Package ``netifaces`` contains a platform-specific binary.
   To install ``netifaces`` from source on Linux, you may also
   need the ``python-dev`` package matching your Python runtime.


On Linux, you may be able to install these components from your
system's distribution packages. Make sure those packages contain
appropriate versions of software listed above and work with the
Python package(s) you may be using.

Building application's distribution from the source files
=========================================================

.. _prereqs-build:

Prerequisites
-------------

To build this application, you need the following software installed
in addition to the above `runtime prerequisites`_:

+---------------------------------------------------+----------+
| Name / Download URL                               | Version  |
+===================================================+==========+
|| GNU gettext                                      || 0.18.1  |
|| https://www.gnu.org/software/gettext/            || or newer|
+---------------------------------------------------+----------+

.. template row
   |                                                   |          |
   |                                                   |          |
   +---------------------------------------------------+----------+
   
