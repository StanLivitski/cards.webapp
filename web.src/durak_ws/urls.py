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
durak_ws URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url
from . import intro, chat, table

_STYLE_RE = r'[^">]*'

urlpatterns = [
    url(r'^$', intro.IntroView.as_view(), name='intro'),
    url('^join/' + r'([a-z]*)$',
        intro.IntroView.as_view(), name='intro'),
    url('^intro$', intro.IntroView.as_view(updateMode=True), name='intro-updates'),
    url('^chat$', chat.ChatView.as_view(), name='chat'),
    url('^messages$', chat.ChatView.as_view(updateMode=True), name='chat-messages'),
    #url(r'^comety/events.js$', TemplateView.as_view(template_name='comety/events.js'), name='test'),
    url(r'^table$', table.TableView.as_view(), name='table'),
    url(r'^table/dimmer/(?P<style>%s)$' % _STYLE_RE,
        table.dimmer_view, name='dimmer'),
    url(r'^game$', table.TableView.as_view(updateMode=True), name='table-updates'),
]
