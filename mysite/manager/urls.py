# -*- coding: utf-8 -*-
from django.conf.urls import *

from mysite.base import views

urlpatterns = patterns('',
   url(r'^$', views.manager),
   url(r'^login/$', views.login),
   url(r'^getDevInfo/$', views.getDevInfo),
   url(r'^loadUrl/$', views.loadUrl),
   url(r'^(?P<fileName>.*)$', views.html),
   )

