#!/usr/bin/env python
# -*- coding:utf-8 -*-

from django.apps import apps
from django.conf import settings

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_migrate
from django.core import checks
from .checks import check_user_model
# from .management import post_superuser_permissions


class BaseConfig(AppConfig):
    name = 'mysite.base'
    label = "base"
    verbose_name = _('系统权限')

    def ready(self):
        # TODO change this code
        # post_migrate.connect(post_superuser_permissions, dispatch_uid="mysite.base.management.post_superuser_permissions")
        # checks.register(check_user_model, checks.Tags.models)
        # checks.register(check_models_permissions, checks.Tags.models)
       	pass
