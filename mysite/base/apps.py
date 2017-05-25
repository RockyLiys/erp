#!/usr/bin/env python
# -*- coding:utf-8 -*-

from django.apps import apps
from django.conf import settings

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.core import checks
from django.db.models.signals import post_migrate


class BaseConfig(AppConfig):
    name = 'mysite.base'
    verbose_name = _('base')

    def ready(self):
        # TODO change this code
        # post_migrate.connect(create_permissions, dispatch_uid="django.contrib.auth.management.create_permissions" )
        # checks.register(check_user_model, checks.Tags.models)
        # checks.register(check_models_permissions, checks.Tags.models)
        pass
