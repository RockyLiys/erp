#!/usr/bin/env python
# -*- coding:utf-8 -*-

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext_lazy as _


class CustomUser(AbstractUser):
    identified = models.CharField(max_length=100, blank=True, null=True)
    USERNAME_FIELD = 'username'

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _("用户")
