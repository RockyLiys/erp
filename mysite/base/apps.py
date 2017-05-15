#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

class BaseConfig(AppConfig):
    name = 'mysite.base'
    module = _('base')
