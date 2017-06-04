#!/usr/bin/env python
# -*- coding:utf-8 -*-

# !/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Group, Permission, AbstractUser, UserManager


class CustomPermission(Permission):
    class Meta:
        verbose_name = _('用户权限')
        verbose_name_plural = _("用户权限")


class CustomGroup(Group):
    class Meta:
        verbose_name = _('用户组')
        verbose_name_plural = _("用户组")


class CustomUserManager(UserManager):
    pass


class CustomUser(AbstractUser):
    identifier = models.CharField(_("身份证"), max_length=40, blank=True, null=True)
    USERNAME_FIELD = 'username'

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _("用户")

    def __str__(self):
        return u'{0}'.format(self.username)
