#!/usr/bin/env python
# -*- coding:utf-8 -*-
CACHE_EXPIRE = 300


class ModelAdmin:
    search_fields = ()
    list_filter = ()
    list_display = ()
    cache = CACHE_EXPIRE
    log = True
    visible = True
    menu_index = 9999
    read_only = False
