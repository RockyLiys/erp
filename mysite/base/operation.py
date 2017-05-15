#!/usr/bin/env python
# -*- coding:utf-8 -*-
import types
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django import forms
from django.db.models.query import QuerySet
import sys
import datetime

# from mysite.base.models_logentry import LogEntry


class ModelOperation(object):
    u"""
    对数据进行特定操作
    """
    params = ()  # 指定前端需传回服务器的参数
    verbose_name = ""  # 在页面上显示该操作的名称
    help_text = ""  # 该操作的提示信息
    model = None
    for_model = True
    confirm = True
    item_index = 9999
    visible = True  # 是否显示

    @classmethod
    def permission_code(cls, model_name):
        cn = "%s_%s" % (cls.__name__.lower(), model_name.lower())
        if cn.find('_') == 0: cn = cn[1:]
        return cn

    def __init__(self, model, verbose_name=None):
        self._MultiSelect = {}
        self.model = model
        self.operation_name = self.__class__.__name__
        if verbose_name:
            self.verbose_name = verbose_name

    def action(self):  # 在此写入实际的数据操作代码
        pass

    def has_permission(self, user):  # 根据当前用户和实际的对象判断是否有权限进行此项操作
        return True

    def form(self, form_field=None, lock=False, init_data={}, post=None):
        f = forms.Form(post)
        for p in self.params:
            key = p[0]
            if isinstance(p[1], models.Field):
                if isinstance(p[1], models.ManyToManyField):
                    rel_model = p[1].rel.to
                    self._MultiSelect[key] = rel_model
                f.fields[key] = form_field and form_field(p[1], readonly=lock and (key in init_data)) or p[
                    1].formfield()
            else:
                f.fields[key] = p[1]
            if key in init_data:
                value = init_data[key]
                if type(value) == list and not isinstance(p[1], models.ManyToManyField):
                    value = value[0]
                f.fields[key].initial = value
                f.initial[key] = value
        f.title = (self.help_text or self.verbose_name) or ""
        return f

    def __unicode__(self):
        return u"%s" % self.verbose_name


class Operation(ModelOperation):
    only_one_object = False
    for_model = False

    def __init__(self, obj):
        super(Operation, self).__init__(obj.__class__)
        self.object = obj
        self.model = obj.__class__

    def can_action(self):  # 根据实际的对象的状态判断是否可以进行该操作
        try:
            return self.object.status == STATUS_OK
        except:
            return True


MIN_DATETIME = datetime.datetime(1, 1, 1)
MAX_DATETIME = datetime.datetime(3000, 1, 1)
NON_FIELD_ERRORS = '__all__'


def parse_value(request, param_name, op):
    value = request.REQUEST.get(param_name, None)
    if value == None: return value
    try:
        return op.rel.to.objects.get(pk=request.REQUEST.get(param_name, None))
    except:
        return value


def chasPerm(user, model, operation):
    modelName = model.__name__.lower()
    perm = '%s.%s_%s' % (model._meta.app_label, operation, modelName)
    return user.has_perm(perm)


class OperationBase(object):
    @classmethod
    def get_all_operations(self, user, ref_model=None):
        for name in dir(self):
            if type(getattr(self, name)) == types.ClassType:
                print("class", name)
                if issubclass(getattr(self, name), ModelOperation):
                    print("operation", name)
        cc = []
        for name in dir(self):
            try:
                if type(getattr(self, name)) == types.TypeType and issubclass(getattr(self, name), ModelOperation):
                    if not name.startswith("_"):
                        tn = name
                    else:
                        tn = name[1:]
                    op = getattr(self, name)
                    perm = '%s.%s_%s' % (self._meta.app_label, tn.lower(), self.__name__.lower())
                    if ref_model:
                        try:
                            _val = ref_model.split('.')
                            perm = '%s.%s_%s' % (_val[0], tn.lower(), _val[1].lower())
                        except:
                            pass
                    if op.visible and user.has_perm(perm):
                        if hasattr(self.Admin, "disable_inherit_perms"):
                            disable_inherit_perms = self.Admin.disable_inherit_perms
                        else:
                            disable_inherit_perms = None
                        if (not disable_inherit_perms) or (name not in disable_inherit_perms):
                            cc.append(name)
            except:
                # 文件字段报错
                pass
            #            return tuple([name for name in dir(self)
            #                    if type(getattr(self, name))==types.TypeType and issubclass(getattr(self, name), ModelOperation)])
        return tuple(cc)

    @classmethod
    def get_operation_js(self, operation):
        op = getattr(self, operation)
        return [u"""
        "%s":{
        verbose_name:"%s",
        help_text:"%s",
        params:%s,
        for_model:%s,
        confirm:%s,
        only_one:%s,
        item_index:%s
        }""" % (operation, op.verbose_name and op.verbose_name.capitalize() or _(op.__name__),
                op.help_text and (" ".join(op.help_text.split("\n")).strip()).capitalize(),
                len(op.params), op.for_model and 'true' or 'false',
                op.confirm and 'true' or 'false',
                (op.for_model or not op.only_one_object) and 'false' or 'true', op.item_index), op]

    @classmethod
    def get_all_operation_js(self, user=None, ref_model=None):
        all_operations = [self.get_operation_js(op) for op in self.get_all_operations(user, ref_model)]
        all_operations.sort(lambda x1, x2: (x1[1].item_index - x2[1].item_index))
        return "{" + (",\n".join([op[0] for op in all_operations])) + "\n}"



        # return "{"+(",\n".join(self.get_operation_js(op) for op in self.get_all_operations(user)))+"\n}"

    @classmethod
    def do_model_action(self, op, request, param={}):

        #        print "do_model_action: param=", param
        try:
            op.request = request
            ret = op.action(**param)
        except Exception as e:
            import traceback;
            traceback.print_exc()
            raise e
        try:
            if param:
                # param=u", ".join([u"%s=%s"%(p[0], unicode(p[1])) for p in param.items()])
                param = u", ".join([u"%s=%s" % (p[0], p[1]) for p in param.items()])
            msg = u"%s %s" % (op.verbose_name, ret or "")
            LogEntry.objects.log_action_other(request.user.pk, self, msg)
        except:
            import traceback;
            traceback.print_exc()
        return ret

    @classmethod
    def do_action_by_request(cls, op, request, form_field):
        op._MultiSelect = {}
        f = None
        try:
            if len(op.params) == 0:
                f = op.form(form_field, post=None)  # f.is_valid ==True----add by darcy 20100430
                ret = do_action(op, request)
            else:
                f = op.form(form_field, post=request.POST)
                if not f.is_valid():
                    return f
                m_ret = f.cleaned_data.copy()
                m_MultiSelect = op._MultiSelect
                if m_MultiSelect:
                    for e in m_MultiSelect.keys():
                        objs = m_MultiSelect[e].objects.filter(pk__in=m_ret[e])
                        m_ret[e] = objs
                ret = do_action(op, request, m_ret)
        except Exception as e:
            import traceback;
            traceback.print_exc()
            if f: ret = u"%s" % e
        if f and ret:
            f.errors[NON_FIELD_ERRORS] = u'<ul class="errorlist"><li>%s</li></ul>' % ret
            return f

    @classmethod
    def model_do_action(cls, action, request, form_field=None, key_name="K"):
        #   print cls, u"model_do_action: %s"%action
        op_class = getattr(cls, action)
        # print issubclass(op_class, ModelOperation)
        if not issubclass(op_class, ModelOperation): raise Exception(u"Error of action name: %s" % action)

        ret = None
        f = None
        if issubclass(op_class, Operation):  # 针对对象的操作

            try:
                if str(request.REQUEST.get("is_select_all", "")) == "1":
                    objs = cls.objects.all()
                else:
                    keys = request.REQUEST.getlist(key_name)
                    objs = cls.objects.filter(pk__in=keys)
                op = op_class(objs[0])

                if hasattr(op, "action_batch"):
                    op = op_class(objs)
                    return cls.do_action_by_request(op, request, form_field)
                for obj in objs:
                    ret = cls.do_action_by_request(op_class(obj), request, form_field)
                    if ret: return ret
            except:
                import traceback;
                traceback.print_exc()
        else:  # ModelOperation，针对模型的操作
            try:
                op = op_class(cls)
                if len(op.params) == 0:
                    f = op.form(form_field, lock=False, init_data=None,
                                post=None)  # 添加f，修改前端无法捕获异常，一直返回正确的bug----add by darcy 20100920
                    ret = cls.do_model_action(op, request)
                else:
                    f = op.form(form_field, lock=request.GET.get('_lock', False), init_data=dict(request.GET),
                                post=request.POST)
                    if not f.is_valid(): return f
                    ret = cls.do_model_action(op, request, f.cleaned_data)
            except Exception as e:
                import traceback;
                traceback.print_exc()
                if f: ret = u"%s" % e
            if f and ret:
                f.errors[NON_FIELD_ERRORS] = u'<ul class="errorlist"><li>%s</li></ul>' % ret
                return f
        return ret


def dump_object(obj):
    t = type(obj)
    if t == tuple: return "(%s)" % (", ".join([dump_object(i) for i in obj]))
    if t in [list, QuerySet]: return "[%s]" % (", ".join([dump_object(i) for i in obj]))
    if t == dict:
        return "(%s)" % (", ".join([u"%s=%s" % (dump_object(key),
                                                dump_object(v)) for key, v in obj.items()]))
    try:
        return u"%s" % obj
    except:
        print("error to dump_object", obj, type(obj))
        return obj


def do_action(op, request, param={}):
    # print "do_action for op, param:%s"%param
    try:
        op.request = request
        if hasattr(op, "action_batch"):
            ret = op.action_batch(**param)
        else:
            ret = op.action(**param)
    except Exception as e:
        import traceback;
        traceback.print_exc()
        raise e
    try:
        if param:
            param = dump_object(param)
        msg = u"%s%s %s" % (op.verbose_name, param or "", ret or "")
        if isinstance(op.object, models.Model):
            LogEntry.objects.log_action_other(request.user.pk, op.object, msg)
        else:
            for obj in op.object:
                LogEntry.objects.log_action_other(request.user.pk, obj, msg)
    except:
        import traceback;
        traceback.print_exc()
    return ret
