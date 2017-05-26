#!/usr/bin/env python
# -*- coding:utf-8 -*-

from django.apps import apps
from django.conf import settings

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.core import checks
from django.db.models.signals import post_migrate
from mysite.base.auth_model import post_syncdb_append_permissions


class BaseConfig(AppConfig):
    name = 'mysite.base'
    verbose_name = _('base')

    def ready(self):
        # TODO change this code
        post_migrate.connect(post_syncdb_append_permissions)
        # checks.register(check_user_model, checks.Tags.models)
        # checks.register(check_models_permissions, checks.Tags.models)
