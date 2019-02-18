..
   Copyright 2016, 2019 Stan Livitski
   
   Licensed under the Apache License, Version 2.0 with modifications
   and the "Commons Clause" Condition, (the "License"); you may not
   use this file except in compliance with the License. You may obtain
   a copy of the License at

    https://raw.githubusercontent.com/StanLivitski/cards.webapp/master/LICENSE

   The grant of rights under the License will not include, and the License
   does not grant to you, the right to Sell the Software, with the
   exception of certain modifications or additions thereto submitted to the
   Licensor by third parties.

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

Dependencies
============

To run this application, you need the following software installed
on your device:

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
|| Bootstrap                                        |3.3.7     |
|| https://getbootstrap.com/docs/3.3/               |          |
+---------------------------------------------------+----------+
|| jQuery                                           |3.2.1     |
|| https://code.jquery.com/jquery/                  |          |
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

Connecting dependencies to the application  
==========================================

The above dependencies include:

 - the Python platform
 - Django and other Python libraries installed as modules within
   your Python platform or a virtual environment
 - JavaScript and CSS libraries

The Python platform and its modules should be configured to enable
running this application within its context.

JavaScript and CSS libraries have to be linked into the application
as shown in the table below. Link locations are relative to the
application's base directory.

+---------------+---------------------------------------+----------------------------------------+
| Resource      | Link target                           | Link location                          |
+===============+=======================================+========================================+
| jQuery        || ``jquery.js`` *or*                   |``web.src/durak_ws/static/js/jquery.js``|
|               || ``jquery.min.js``                    |                                        |
+---------------+---------------------------------------+----------------------------------------+
| Bootstrap     || ``bootstrap*-dist/``                 |``web.src/durak_ws/static/bootstrap``   |
|               || *(unpacked distribution              |                                        |
|               |  directory) or*                       |                                        |
|               || ``/usr/share/javascript/bootstrap/`` |                                        |
+---------------+---------------------------------------+----------------------------------------+

.. template row
   |               |                                       |                                        |
   |               |                                       |                                        |
   +---------------+---------------------------------------+----------------------------------------+

---------------------------------------------------------
Building application's distribution from the source files
---------------------------------------------------------

Prerequisites
=============

To build this application, you need the following software installed
in addition to the above `dependencies`_:

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

.. _gpl_component_tweaking:
   
--------------------------------
Adding and replacing card images
--------------------------------

You can add or replace images of card backs and change images of
card faces displayed by the application by saving alternative or
modified images in the ``cards.webapp`` directories of ``svg-card-backs``
and ``responsive-playing-cards`` subprojects (under ``downloads/``).
Note that replacement images must satisfy requirements
listed in the comments of XSL Transformation (``.xslt``) files within
those directories.

XSL Transformations in the subprojects containing card images were used to
convert images from the upstream projects. You can run them again to import
any updates to the upstream images.

To have the application display card images installed elsewhere on a
hosting system, run the ``link_card_images.py`` script from ``misc/scripts/``.
Note that this script has additional dependencies which are listed in its
docstring. When running the script, specify either ``front/`` or
``back/`` subdirectory of ``web.src/durak_ws/static/cards/images`` in the
project's sources as the target and the permanent location of your images
as the source.
