#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.contrib import admin
CACHE_EXPIRE = 300


class ModelAdmin(admin.ModelAdmin):
    cache = CACHE_EXPIRE
    log = True
    visible = True
    menu_index = 9999
    read_only = False
