﻿#!/usr/bin/env python
# -*- coding:utf-8 -*-

from django.utils.encoding import smart_str
from django.forms import forms

from simplejson import dumps
# from mysite.base.dbapp import widgets
from mysite.base.grid_utils import GridBase


class AppPage(object):
    verbose_name = None
    app_menu = None
    menu_index = 0
    context = {}
    template = 'app_page.html'
    visible = False

    def __init__(self, request=None):
        pass


class GridModel(AppPage):
    verbose_name = None
    app_menu = None
    menu_index = 0
    m_context = {}
    template = 'grid_model.html'
    visible = False

    head = {}
    option = {}
    search_form = []
    hide_list = []
    #    buttons = []#[{},{}]
    grid = None
    _paged = False

    def __init__(self, request=None):
        self.hide_list = []
        self.grid = GridBase(self.head, self._GetPageSize())
        self.request = None
        self.m_context = {}

    def GetHeads(self):
        return self.grid.fields

    def Paging(self, offset, item_count=None):
        self.grid.paging(offset=offset, item_count=item_count)
        self._paged = True

    def SetPageSize(self, psize):
        self.grid.pagesize = psize
        # self.option["rp"] = psize

    def _GetPageSize(self):
        if self.option.has_key("rp"):
            return self.option["rp"]
        else:
            return 15

    def ParseLike(self, request):
        search_fields = [e[0] for e in self.search_form]
        for m in search_fields:
            data = request.REQUEST.get(m, '')
            if data:
                self.grid.sql += " and %s like '%%%%%s%%%%'" % (m, data)

    def context(self):
        m_HeadDic = self.grid.HeadDic()
        m_init_option = {
            "url": "/grid/%s/%s/" % (self.app_menu, self.__class__.__name__),
            "dataType": "json",
            "usepager": True,
            "useRp": True,
            "rp": 15,
            "showTableToggleBtn": True,
            "onToggleCol": '$do_ToggleCol$',
            "onSubmit": '$do_Submit$',
            "pagestat": '显示 {from} 到 {to} ,共 {total} 条记录',
            'nomsg': '无记录',
            'procmsg': '正在处理中...',
            'pagetext': '第',
            'outof': '页 / 共',
            'findtext': '查找'
        }
        m_init_option.update(self.option)
        m_HeadDic.update(m_init_option)
        addition = {"grid_option": smart_str(dumps(m_HeadDic)).replace('"$', '').replace('$"', '')}
        addition["hide_list"] = self.hide_list
        if self.search_form:
            ''' 查询表单的处理 '''

            form = forms.Form()
            for e in self.search_form:
                field = e[1]
                widget = None
                if field.__class__ in widgets.WIDGET_FOR_DBFIELD_DEFAULTS:
                    widget = widgets.WIDGET_FOR_DBFIELD_DEFAULTS[field.__class__]
                if widget:
                    form_field = field.formfield(widget=widget)
                    if hasattr(field, 'add_attrs'):
                        form_field.widget.attrs.update(field.add_attrs)
                        # form_field.widget_attrs = lambda o,w:field.add_attrs
                    form.fields[e[0]] = form_field
                else:
                    form.fields[e[0]] = field.formfield()
            addition["search_form"] = form
        addition.update(self.m_context)
        return addition

    def MakeData(self, request, **arg):
        '''
        组装 items 或 组装sql语句
        '''
        pass

    def SetBlank(self):
        self.Paging(1)
        self.grid.blank = True

    def SetHide(self, filed):
        self.grid.fields[filed]["hide"] = True
        self.hide_list.append(self.grid.GetFieldNames().index(filed))

    def AddContext(self, m_dict):
        self.m_context.update(m_dict)
