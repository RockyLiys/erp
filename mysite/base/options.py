#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import models
from django import forms
from django.core.cache import cache
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext
import re

# from mysite.utils import get_option
# from mysite.base.backup import get_attsite_file
from mysite.base.cached_model import CachingModel
from mysite.base.operation import OperationBase, Operation, ModelOperation
from mysite.base.middleware import threadlocals
from mysite.base.base_code import BaseCode
from mysite.base.translation import DataTranslation

SYSPARAM = "1"
PERSONAL = "2"


class Option(CachingModel):
    """
    """
    name = models.CharField(max_length=30)  # 名称
    app_label = models.CharField(max_length=30)  # 应用
    catalog = models.CharField(max_length=30)  # 分类
    group = models.CharField(max_length=30)  # 分组
    widget = models.CharField(max_length=400)  # 输入控件
    required = models.BooleanField()  # 是否必须
    validator = models.CharField(max_length=400)  # 输入数据的检验条件
    verbose_name = models.CharField(max_length=80)  # 该选项的显示名称，在界面上显示的名称
    help_text = models.CharField(max_length=160)  # 对该选项的详细说明，在界面上显示的提示信息
    visible = models.BooleanField()  # 是否在界面上可见
    default = models.CharField(max_length=100)  # 默认值
    read_only = models.BooleanField(default=False)  # 是否可以修改
    for_personal = models.BooleanField(default=True)  # 是否可以个性化
    type = models.CharField(max_length=50, default='CharField')  # 数据类型

    class Admin(CachingModel.Admin):
        log = False
        visible = False

    class Meta:
        verbose_name = _(u'个性设置')

    def __unicode__(self):
        return u"%s.%s" % (ugettext(self.app_label),
                           self.verbose_name and ugettext(self.verbose_name) or self.name)

    def form_field(self, catalog, user=None):
        args = {}

        objs = BaseCode.objects.filter(content='%s.%s' % (self.app_label, self.name))
        if objs.count() > 0:
            f = forms.fields.ChoiceField
            args['choices'] = [(o.value, DataTranslation.get_obj_display2(o, 'display')) for o in objs]
        else:
            try:
                f = getattr(forms, self.type or "CharField")
            except:
                f = forms.CharField

        if self.widget: args['widget'] = getattr(forms.widgets, self.widget)
        args['required'] = self.required
        args['label'] = _(self.verbose_name or self.name)
        args['initial'] = self.default
        if user:
            try:
                p = PersonalOption.objects.get(option=self, user=user)
                args['initial'] = p.value
            except:
                pass
        if catalog == SYSPARAM:
            try:
                p = SystemOption.objects.get(option=self)
                args['initial'] = p.value
            except:
                pass

        if self.help_text: args['help_text'] = _(self.help_text)
        return f(**args)

    @staticmethod
    def create_form_fields(catalog, user=None):
        fields = {}
        for o in Option.objects.filter(catalog=catalog, visible=True):
            fields["%s.%s" % (o.app_label, o.name)] = o.form_field(catalog, user)  # 把本条记录的所有值作为一个form字段的属性返回
        return fields


class OptionForm(forms.Form):  # 个性化表单
    profile_fields = ['first_name', 'last_name', 'email']

    def __init__(self, catalog, user=None, *args, **kwargs):
        super(OptionForm, self).__init__(*args, **kwargs)
        if user:
            for a in dir(user):
                if a in self.profile_fields:
                    user = User.objects.get(pk=user.pk)
                    self.fields[a] = user.__class__._meta.get_field(a).formfield(initial=getattr(user, a))
        self.fields.update(Option.create_form_fields(catalog, user))  # 合并上面三个字段以及参数表中的字段
        self.user = user

    def clean_email(self):
        vv = self.cleaned_data["email"].strip()
        if vv == "":
            #                raise forms.ValidationError(u"%s"%_(u"请输入邮箱"))
            return vv
        if not re.search(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$", vv):
            raise forms.ValidationError(u"%s" % _(u"邮箱格式不正确"))
        return vv

    def save(self):
        " 保存表单到数据库 "
        modified = False
        if self.user:
            for a in dir(self.user):
                if a in self.profile_fields:
                    try:
                        value = self.cleaned_data[a]
                        if not (value == getattr(self.user, a)):
                            modified = True
                            setattr(self.user, a, value)
                    except:
                        pass
            if modified:
                self.user.save()

        for item, value in self.cleaned_data.items():
            if item not in self.profile_fields:
                if self.user and not (self.user.is_anonymous()):
                    options[item] = value
                else:
                    options.save_to_system(item, value or "")


class SystemOption(CachingModel):
    option = models.ForeignKey(Option)
    value = models.CharField(max_length=100)

    class Admin(CachingModel.Admin):
        help_text = _(u"系统参数即系统的一些设置项！")
        visible = False
        menu_index = 500

    class Meta:
        verbose_name = _(u"系统参数")
        verbose_name_plural = _(u"系统参数")



class AppOption(CachingModel):
    optname = models.CharField(_(u'参数名字'), max_length=50, default="")
    value = models.CharField(_(u'参数值'), max_length=100, default="")
    discribe = models.CharField(_(u'描述'), max_length=100, null=True, blank=True)

    def __unicode__(self):
        return self.optname + "(" + self.value + ")"

    class _clear(ModelOperation):
        help_text = _(u"清空所有记录")  # 清除该表的全部记录
        verbose_name = _(u"清空记录")
        visible = False

        def action(self):
            pass

    class _add(ModelOperation):
        help_text = _(u"新增记录")  # 新增记录
        verbose_name = _(u"新增")
        visible = False

        def action(self):
            pass

    class _delete(Operation):
        help_text = _(u"删除选定记录")  # 删除选定的记录
        verbose_name = _(u"删除")
        visible = False

        def action(self):
            pass

    def save(self, **args):
        tmp = AppOption.objects.filter(optname=self.optname)
        if len(tmp) > 0 and tmp[0].id != self.id:  # 新增
            raise Exception(_(u'%s已经存在!') % self.optname)
        if self.optname == "browse_title":
            cache.delete("browse_title")
        if self.optname == "msg_scanner" or self.optname == "pos_scanner":
            sp = self.value.split(":")
            if len(sp) != 2 or (not sp[0].isdigit() or not sp[1].isdigit()):
                raise Exception(u"%s" % _(u'日期格式不正确,请重新输入(hh:mm)!'))
        if self.optname == "dbversion":
            raise Exception(u"%s" % _(u'版本不支持修改！'))

        super(AppOption, self).save(**args)

    class Admin(CachingModel.Admin):
        help_text = _(u"系统参数即系统的一些设置项，如消息监控时间，\n系统会根据此参数值来监控过生日和转正的人员！")  # get_option("APPOPTION_HELP_TEXT")
        cache = False
        disabled_perms = ["add_appoption", "clear_appoption", "delete_appoption"]
        list_filter = ['optname', 'value']
        list_display = ['optname', 'value', 'discribe']
        menu_index = 501

        def initial_data(self):
            # if not AppOption.objects.filter(optname='backup_sched', value='0'):
            # AppOption(optname="backup_sched",value='0',discribe=u'备份时间').save()
            if not AppOption.objects.filter(optname='company'):
                AppOption(optname="company", value='Company Name', discribe=u"%s" % _(u'公司名称')).save()

            if not AppOption.objects.filter(optname='dbversion'):
                dict = get_attsite_file()
                dbversion = dict["Options"]["Version"]
                # print version,'----------version'
                if dbversion:
                    super(AppOption,
                          AppOption(optname="dbversion", value=str(dbversion), discribe=u"%s" % _(u'数据库版本'))).save()

            from mysite import settings
            acc = get_option("IACCESS")
            att = get_option("ATT")
            pos = get_option("POS")
            #                    if att and not get_option("IACCESS_WITH_ATT") and not AppOption.objects.filter(optname='msg_scanner'):
            if not AppOption.objects.filter(optname='msg_scanner'):
                AppOption(optname="msg_scanner", value='07:01', discribe=u"%s" % _(u'消息监控时间')).save()

            if pos and not AppOption.objects.filter(optname='pos_scanner'):
                AppOption(optname="pos_scanner", value='03:01', discribe=u"%s" % _(u'消费卡状态监控时间')).save()


                # if acc and not AppOption.objects.filter(optname='download_time'):
                # AppOption(optname="download_time", value='0', discribe=u"%s" % _(u'定时下载时间')).save()

            if not AppOption.objects.filter(optname='browse_title'):
                title = get_option("APPOPTION_BROWSE_TITLE")
                AppOption(optname="browse_title", value=u"%s" % title, discribe=u"%s" % _(u'浏览器标题')).save()

    class Meta:
        verbose_name = _(u"系统参数")
        verbose_name_plural = _(u"系统参数")



class AppOptionClass(object):
    def __getitem__(self, optname):
        try:
            value = AppOption.objects.get(optname=optname).value
            return value
        except Exception as e:
            return None

    def __setitem__(self, item, value):
        try:
            param = AppOption.objects.get(optname=item)
            if len(param) != 0:
                param.optname = item
                param.value = value
                param.save()
            return value
        except Exception as e:
            return None


appOptions = AppOptionClass()


class PersonalOption(CachingModel):
    """
    """
    option = models.ForeignKey(Option)
    value = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)  #

    class Admin(CachingModel.Admin):
        cache = False
        menu_index = 500
        visible = False

    class Meta:
        verbose_name = _(u"个人选项")
        unique_together = ('option', 'user')
        verbose_name_plural = _(u"个人选项")
        


class OptionClass(object):
    _cache = {}

    def __init__(self):
        pass

    def __getitem__(self, item):
        # if item in self._cache:        return self._cache[item]
        op = threadlocals.get_current_user()
        if op and op.is_anonymous(): op = None
        if '.' not in item:
            value = getattr(settings, item)
        else:
            items = item.split(".", 1)
            value = None
            try:
                opt = Option.objects.get(app_label=items[0], name=items[1])
            except ObjectDoesNotExist:
                return None
            try:
                if op:
                    opt = PersonalOption.objects.get(option=opt, user=op)
                    value = opt.value
            except ObjectDoesNotExist:
                pass
            if value == None:
                try:
                    opt = SystemOption.objects.get(option=opt)
                    value = opt.value
                except ObjectDoesNotExist:
                    value = opt.default
            self._cache[item] = value
        return value

    def __setitem__(self, item, value):
        """
        修改一个系统配置项的值到用户个性化设置中，这主要用于系统运行期保存一些个性化的参数设置。
        """
        if self.__getitem__(item) == value: return
        if item in self._cache: self._cache.pop(item)
        op = threadlocals.get_current_user()
        if op and op.is_anonymous(): op = None
        items = item.split(".", 1)
        opt = Option.objects.get(app_label=items[0], name=items[1])
        try:
            p_opt = PersonalOption.objects.get(option=opt, user=op)
        except ObjectDoesNotExist:
            p_opt = PersonalOption(option=opt, user=op)  # create it if not exists
        if not (p_opt.value == value):
            p_opt.value = value
            p_opt.save()
            if item == 'base.language':
                from django.utils.translation import check_for_language, activate, get_language
                request = threadlocals.get_current_request()
                if request:
                    lang_code = value
                    if lang_code and check_for_language(lang_code):
                        if hasattr(request, 'session'):
                            request.session['django_language'] = lang_code
                            activate(lang_code)
                            request.LANGUAGE_CODE = get_language()
        self._cache[item] = value

    def save_to_system(self, item, value):
        """
        修改一个系统配置项的值到整个系统中，这主要用于系统运行期保存一些全局的参数设置。
        """
        if item in self._cache: self._cache.pop(item)
        items = item.split(".", 1)
        opt = Option.objects.get(app_label=items[0], name=items[1])
        try:
            opt = SystemOption.objects.get(option=opt)
        except ObjectDoesNotExist:
            opt = SystemOption(option=opt)
        if not (opt.value == value):
            opt.value = value
            opt.save()
        return opt

    def add_option(self, item, default, verbose_name, help_text, catalog, visible=True):
        """
        添加一个配置项。该函数主要用于系统初始化时设定一些参数。
        """
        items = item.split(".", 1)
        value = None
        try:
            opt = Option.objects.filter(app_label=items[0], name=items[1])[0]
            opt.value = default
            opt.verbose_name = verbose_name
            opt.help_text = help_text
            opt.catalog = catalog
            opt.visible = visible
            opt.save()
        except IndexError:  # ObjectDoesNotExist:
            opt = Option(app_label=items[0], name=items[1], default=default, verbose_name=verbose_name,
                         help_text=help_text, catalog=catalog, visible=visible)
            opt.save()
        return opt


options = OptionClass()
