#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.contrib import admin

# Register your models here.
from mysite.base.models_addition import AdditionData
from mysite.base.models_logentry import LogEntry
from mysite.base.modeladmin import ModelAdmin
from mysite.base.auth_model import CustomUser, CustomGroup, CustomPermission


@admin.register(LogEntry)
class CachingModelAdmin(ModelAdmin):
    # search_fields = ('name',)
    pass


@admin.register(AdditionData)
class AdditionDataAdmin(ModelAdmin):
    pass


@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    pass

@admin.register(CustomGroup)
class CustomGroupAdmin(ModelAdmin):
    pass


@admin.register(CustomPermission)
class CustomPermissionAdmin(ModelAdmin):
    pass
