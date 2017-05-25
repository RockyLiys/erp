#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import connection
from django.contrib.auth.models import User, Permission, Group
from traceback import print_exc
from django.core.management import call_command
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import NOT_PROVIDED
from mysite.base.dj6 import dict4ini

from django.conf import settings
from django.db.models import Q
# from django.contrib.auth.management import create_superuser
# from django.db.models.signals import post_syncdb
# from south.db import db
import os

from mysite.base.dj6.loading import AppCache
from mysite.base.custom_model import AppPage
from mysite.base.models_logentry import LogEntry
from mysite.base.cached_model import CachingModel
from mysite.base.base_code import BaseCode, base_code_by
from mysite.base.operation import Operation, ModelOperation
from mysite.base.options import Option, SystemOption, PersonalOption, options, AppOption, appOptions, SYSPARAM, PERSONAL
from mysite.base.translation import *

# from mysite.base.sync_contenttype import update_all_contenttypes

from mysite.base.auth_model import CustomUser

unicode = str
verbose_name = _(u"系统设置")
_menu_index = 9


class AppOperation(object):
    pass


# 替换django.db.models.ManyToManyField, 因为其控件总是显示多选的操作提示，而很多多选控件与此不一致“”
# if hasattr(models.ManyToManyField, "old_m2m"):
#     pass
# else:
#     class ZManyToManyField(models.ManyToManyField):
#         old_m2m = models.ManyToManyField

#         def __init__(self, to, **kwargs):
#             super(ZManyToManyField, self).__init__(to, **kwargs)
#             if 'help_text' in kwargs:
#                 self.help_text = kwargs['kwargs']
#             else:
#                 self.help_text = ""


#     models.ManyToManyField = ZManyToManyField


class InvisibleAdmin(CachingModel.Admin):
    visible = False


class NoLogAdmin(CachingModel.Admin):
    log = False


def is_parent_model(pm, m):
    u''' 检查 模型 pm 是否模型 mo 的所属类型，即是否其外键或级联外键 '''
    if pm == m: return True
    for f in m._meta.fields:
        if isinstance(f, models.fields.related.ForeignKey):
            if not f.rel.to == m:  # 避免产生无穷递归
                if is_parent_model(pm, f.rel.to): return True
    return False


def custom_sql(sql, action=True):
    cursor = connection.cursor()
    cursor.execute(sql)
    if action:
        connection._commit()
    return cursor


def try_add_permission(ct, cn, cname):
    try:
        Permission.objects.get(content_type=ct, codename=cn)
    except:
        try:
            Permission(content_type=ct, codename=cn, name=cname).save()
            # print "Add permission %s OK"%cn
        except Exception as e:
            print("Add permission %s failed:" % cn, e)


def check_and_create_app_permission(app_label, operation):
    '''
    添加 can_operation 权限
    '''
    if not hasattr(operation, '_parent_model'):
        ct = ContentType.objects.filter(app_label=app_label, model=operation.__name__.lower())[0]
        try_add_permission(ct, 'can_' + operation.__name__, u"%s主页" % operation.verbose_name)
    else:
        name = operation._parent_model.lower()
        ct = ContentType.objects.filter(app_label=app_label, model=name)[0]
        try_add_permission(ct, 'can_' + operation.__name__, u"%s" % operation.verbose_name)


def get_model_from_keystr(keystr):
    try:
        ret = keystr.split('.')
        return AppCache().app_models.get(ret[0]).get(ret[1])
    except:
        return None


def get_app_label_from_app(app):
    plist = app.__name__.split('.')
    if len(plist) == 3:
        return plist[1]
    elif len(plist) == 2:
        return plist[0]
    else:
        return None


def check_and_create_model_permissions(model):
    if hasattr(model, "check_and_create_model_permissions"): return
    ct = ContentType.objects.get_for_model(model)
    cn = 'browse_' + model.__name__.lower()
    cname = u'浏览'  # u'浏览%s' % model._meta.verbose_name
    try_add_permission(ct, cn, cname)
    for perm in model._meta.permissions:
        try_add_permission(ct, perm[0], perm[1])
    for op_name in dir(model):
        try:
            op = getattr(model, op_name)
            if issubclass(op, ModelOperation) and op.visible:
                if hasattr(model.Admin, "disable_inherit_perms"):
                    disable_inherit_perms = model.Admin.disable_inherit_perms
                else:
                    disable_inherit_perms = None
                if hasattr(op, 'perm_model_menu'):
                    _perm_model_menu = op.perm_model_menu
                    for e in _perm_model_menu:
                        _model = get_model_from_keystr(e)
                        if _model:
                            _ct = ContentType.objects.get_for_model(_model)
                        else:
                            ret = e.split('.')
                            try:
                                _ct = ContentType.objects.filter(app_label=ret[0], model=ret[1].lower())[0]
                            except:
                                _ct = None
                        if _ct:
                            if (not disable_inherit_perms) or (op_name not in disable_inherit_perms):
                                cn = op.permission_code(_ct.model)
                                cname = u"%s" % (op.verbose_name)
                                try_add_permission(_ct, cn, cname)
                else:
                    cn = op.permission_code(model.__name__)
                    cname = u"%s" % (op.verbose_name)
                    try_add_permission(ct, cn, cname)
        except TypeError:
            pass
        except AttributeError:
            pass
        except:
            print_exc()
    model.check_and_create_model_permissions = True


def search_field(model, s):
    from django.db import connection
    for f in model._meta.fields:
        fn = "%s.%s" % (model._meta.db_table, f.column)
        if 'sqlserver_ado' in connection.__module__:
            fn = "%s" % f.column
        if fn in s:
            return f


def check_and_create_model_new_fields(model):
    c = 0
    for i in range(40):
        hc = 0
        try:
            d = list(model.objects.filter(pk=0))
        except Exception as e:
            info = u"%s" % e
            infos = info.replace('"', ' ').replace("'", " ").replace(",", ' ').replace(". ", " ").split(" ")
            f = search_field(model, infos)
            hc += 1
            # if f:
            # print info
            # print("add_field: ", model.__name__, f.name, "... ",)
            # try:
            #     db.add_column(model._meta.db_table, f.name, f)
            # except:
            #     if not f.null and not f.has_default():
            #         f.default = f.get_default()
            #         if f.default is None: f.default = 1
            #     db.add_column(model._meta.db_table, f.name, f)
            #     print(f.null, f.has_default(), f.default)
            # print(" OK")
            # c += 1
        if hc == 0: break;
    return c


def check_and_create_model_default(model):
    db_table = model._meta.db_table
    for f in model._meta.fields:
        if not (f.default == NOT_PROVIDED):
            db_column = f.db_column or f.column
            value = "'%s'" % f.get_default()
            sql = "ALTER TABLE %s ADD CONSTRAINT default_value_%s_%s DEFAULT %s FOR %s" % (
            db_table, db_table, db_column, value, db_column)
            try:
                custom_sql(sql)
            except:
                pass


def search_object(model, data, append=True):
    for field in data:
        try:
            f = model._meta.get_field(field)
        except:
            continue
        value = data[field]
        if isinstance(f, models.fields.related.ForeignKey):
            if type(value) == type({}):  #
                objs = search_object(f.rel.to, value, append)
                value = objs[0]
                data[field] = value
    udata = dict([(k.replace("_id", ""), unicode(v)) for k, v in data.items()])  # value需要unicode
    objs = model.objects.filter(**udata)  # 初始化前先判断当前数据是否已经添加过--darcy20100714
    if append and len(objs) == 0:
        obj = model(**udata)
        obj.save()
        objs = [obj, ]
    return objs


def check_and_create_model_initial_data(model):
    if not hasattr(model, "Admin"): return
    if not hasattr(model.Admin, "initial_data"): return
    datas = getattr(model.Admin, "initial_data")
    if type(datas) in (list, tuple):
        for data in datas:
            try:
                obj = search_object(model, data, True)
            except:
                print('-----error-----')
                print_exc()
    elif callable(datas):
        model.Admin().initial_data()


def check_and_create_app_options(app):
    print("check and create app options:", app.__name__)
    p0, p1 = os.path.split(os.path.split(app.__file__)[0])
    if p1 == 'models':
        p1 = os.path.split(p0)[1]
    if hasattr(app, "app_options"):
        ao = app.app_options
        if callable(ao):
            ao = ao()
        for o in ao:
            try:
                options.add_option(p1 + "." + o[0], o[1], o[2], o[3], o[4], o[5])
            except:
                print('----------', o[0], o[1], o[2], o[3], o[4], o[5], '-----------')
                import traceback;
                traceback.print_exc()


def post_syncdb_append_permissions(sender, **kwargs):
    u"""
    1、升级数据库结构, 设置字段默认值
    2、导入初始数据
    3、创建操作权限
    """
    # 创建一个超级用户
    if not User.objects.filter(username="admin"):
        User.objects.create_superuser("admin", "admin@sina.com", "admin")

    # 同步数据库的时候加入国际化，现在按照settings
    # 里面的LANGUAGE_CODE参数来初始化，所以打包不同语言时需要手工改变此参数 pwp

    language = settings.LANGUAGE_CODE

    app = sender
    if app.__name__ == "base.models":
        call_command('loaddata', 'initial_data_' + language, verbosity=1, database="default")
    created_models = list(kwargs['created_models'])
    verbosity = kwargs["verbosity"]
    interactive = kwargs["interactive"]

    # 根据语言参数国际化ContentType中的name值
    translation.activate(language)
    # update_contenttypes(sender,created_models,verbosity=verbosity,interactive=interactive)
    # update_all_contenttypes()
    translation.activate("en-us")

    all_models = []
    for i in dir(app):
        try:
            model = app.__getattribute__(i)
        except:
            continue
        if callable(model) and type(model) not in [type(issubclass), type(post_syncdb_append_permissions)]:
            try:
                if issubclass(model, models.Model) and not model._meta.abstract:
                    check_and_create_model_new_fields(model)
                    check_and_create_model_default(model)
                    translation.activate("zh-cn")
                    check_and_create_model_permissions(model)
                    translation.activate(language)
                    check_and_create_model_initial_data(model)
                    translation.activate("en-us")
                elif (issubclass(model, AppOperation) and hasattr(model, 'view')) or (
                    issubclass(model, AppPage) and model.visible):
                    translation.activate("zh-cn")
                    check_and_create_app_permission(get_app_label_from_app(app), model)  # 添加 app 权限
                    translation.activate("en-us")
            except:
                print_exc()
    try:
        check_and_create_app_options(app)
        init_self_user()  # 初始化员工自助
    except:
        print_exc()


# post_syncdb.disconnect(create_superuser,
#                        sender=auth_app, dispatch_uid="django.contrib.auth.management.create_superuser")
# post_syncdb.connect(post_syncdb_append_permissions)


def init_self_user():
    u"添加自助查询用户,确保在权限代码都创建完了之后，才可以初始化角色"
    usrs = User.objects.filter(username="employee")

    if not usrs:
        usr = User.objects.create_user("employee", "employee@zksoftware.com", "jq92~+>)@#$%#")
        usr.is_staff = True
        usr.save()
    else:
        usr = usrs[0]
    # 添加自助查询角色
    g_employees = Group.objects.filter(name="role_for_employee")
    if not g_employees:
        g_employee = Group()
        g_employee.name = "role_for_employee"
        g_employee.save()
        usr.groups.add(g_employee)
    else:
        g_employee = g_employees[0]

        # 添加自助查询角色所拥有的权限
    #
    # 同步数据库后,可以在数据库中查看生成的权限值
    # select * from auth_permission ap
    #    inner join django_content_type dct on dct.id = ap.content_type_id
    #    where dct.model ='***'
    # 可以通过下面的方法给员工自助配置code

    self_perms = [
        {
            "app_label": "selfservice",
            "model": "SelfSpecDay",
            "codename": ["can_SelfSpecDay"]
        },
        {
            "app_label": "selfservice",
            "model": "SelfOverTime",
            "codename": ["can_SelfOverTime"]
        },
        {
            "app_label": "selfservice",
            "model": "SelfTransaction",
            "codename": ["can_SelfTransaction"]
        },
        {
            "app_label": "selfservice",
            "model": "SelfCheckexact",
            "codename": ["can_SelfCheckexact"]
        },
        {
            "app_label": "selfservice",
            "model": "SelfReport",
            "codename": ["can_SelfReport"]
        },
    ]
    att_perms = [
        {
            "app_label": "att",
            "model": "EmpSpecDay",
            "codename": ["opaddmanyuserid_empspecday", "browse_empspecday", "change_empspecday", "delete_empspecday"]
        },
        {
            "app_label": "att",
            "model": "OverTime",
            "codename": ["opaddmanyovertime_overtime", "browse_overtime", "change_overtime", "delete_overtime"]
        },
        {
            "app_label": "att",
            "model": "CheckExact",
            "codename": ["opaddmanycheckexact_checkexact", "browse_checkexact", "change_checkexact",
                         "delete_checkexact"]
        },
        {
            "app_label": "att",
            "model": "checkinout",
            "codename": ["can_CheckInOut"]
        },
        {
            "app_label": "att",
            "model": "attreport",
            "codename": ["can_AttReport", ]
        },
    ]
    perms_detail = self_perms + att_perms

    permissions = []
    count_perms = 0
    for e in perms_detail:
        try:
            count_perms += len(e["codename"])
            mct = ContentType.objects.get(app_label=e["app_label"], model=e["model"].lower())
            p = Permission.objects.filter(codename__in=e["codename"], content_type=mct)
            #            if len(p) != len(e["codename"]):
            #                print len(p),len(e["codename"]),'\n'
            #                print e["codename"],'\n'
            permissions.extend(p)
        except:
            #            print 'app_label:',e["app_label"],'model',e["model"],'\n'
            #            import traceback;traceback.print_exc();
            break
        #    print 'count_perms:',count_perms,'\n'
        #    print 'len(permissions):',len(permissions),'\n',[p.codename for p in permissions]
    if count_perms == len(permissions):
        if g_employee.permissions.count() <= count_perms:  # 并且还未初始化
            g_employee.permissions = permissions
        print(
            ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> selfservice permissions sync success! <from python-support\base\models.py>")
    else:
        print(
            "!!! selfservice permissions sync faild==>need permissions:%d,db permissions:%d,please check it ! <from python-support\base\models.py>" % (
            count_perms, len(permissions)))


def app_options():
    appconf = dict4ini.DictIni(settings.APP_HOME + "/appconfig.ini")
    language = appconf["language"]["language"]

    return (
        # 参数名称, 参数默认值，参数显示名称，解释,参数类别,是否可见
        ('date_format', '%Y-%m-%d', u"%s" % _(u'日期格式'), '', PERSONAL, True),
        ('time_format', '%H:%M:%S', u"%s" % _(u'时间格式'), '', PERSONAL, True),
        ('datetime_format', '%Y-%m-%d %H:%M:%S', u"%s" % _(u'时间日期格式'), '', PERSONAL, True),
        ('shortdate_format', '%y-%m-%d', u"%s" % _(u'短日期格式'), '', PERSONAL, True),
        ('shortdatetime_format', '%y-%m-%d %H:%M', u"%s" % _(u'短日期时间格式'), '', PERSONAL, True),
        ('language', language, u'语言', '', PERSONAL, True),
        ('base_default_page', 'data/auth/User/', u"%s" % _(u'系统默认页面'), '', PERSONAL, False),
        ('site_default_page', 'data/worktable/', u"%s" % _(u'整个系统默认页面'), "", PERSONAL, False),
        ('site_default_page', 'data/worktable/', u"%s" % _(u'整个系统默认页面'), "", PERSONAL, False),
        ('backup_sched', '', u'备份时间', "", SYSPARAM, True),
        # ('company','Company Name', u'公司名称', "",SYSPARAM,True),
        # ('browse_title',u'ZKECO企业信息管理系统', u'浏览器标题', "",SYSPARAM,True),
    )


def database_init(sender, **kwargs):
    # print "sender: %s, kwargs: %s"%(sender, kwargs)
    # connection=kwargs['connection']
    # if 'mysql' in connection.__module__:
    #    connection.cursor().execute('set autocommit=1')
    # print "database_init sender: %s, kwargs: %s"%(sender, kwargs)
    from django.db import connection
    if 'mysql' in connection.__module__:
        connection.cursor().execute('set autocommit=1')


from django.db.backends.signals import connection_created

connection_created.connect(database_init)
