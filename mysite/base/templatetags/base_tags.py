#!/usr/bin/env python
# coding=utf-8
import datetime
from django import template
from mysite.base.options import options
from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.cache import cache
from django.db import models
from django.conf import settings

force_unicode = smart_str = str
register = template.Library()


@register.filter
def content_type_str(ct):
    if ct:
        return ct.model_class()._meta.verbose_name
    else:
        return ""


@register.filter
def fmt_datetime(time):
    try:
        return time.strftime(str(options['base.datetime_format']))
    except:
        return ""


@register.filter
def fmt_date(time):
    try:
        return time.strftime(str(options['base.date_format']))
    except:
        return ""


@register.filter
def fmt_time(time):
    try:
        return time.strftime(str(options['base.time_format']))
    except:
        return ""


@register.filter
def fmt_shortdatetime(time):
    try:
        return time.strftime(str(options['base.shortdatetime_format']))
    except:
        return ""


@register.filter
def content_url(s, obj):
    if not obj or (not obj.content_type):
        return s
    m = obj.content_type.model_class()
    return u"<a href='../../%s/%s/%s/?_lock=ALL' class='edit'>%s</a>" % (m._meta.app_label, m.__name__, obj.object_id, s)


@register.filter
def obj_url(obj):
    if not obj:
        return ""
    return u"<a href='../../%s/%s/%s/?_lock=ALL' class='edit'>%s</a>" % (obj._meta.app_label, obj.__class__.__name__, obj.pk, obj)
