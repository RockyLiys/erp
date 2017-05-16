#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.utils.translation import get_language
from django.utils.encoding import force_text, python_2_unicode_compatible

from django.contrib.auth.models import Group, User, Permission, UserManager
from django.contrib.contenttypes.models import ContentType

from mysite.base.models import InvisibleAdmin
from mysite.base.cached_model import CachingModel
from mysite.base.modeladmin import ModelAdmin, CACHE_EXPIRE
from mysite.base.operation import Operation
from mysite.base.custom_model import AppPage
from mysite.base.models import AppOperation

from mysite.base.translation import DataTranslation, _ugettext_ as _
from mysite.base.middleware import threadlocals
from mysite.base.middleware.threadlocals import  get_current_request
from mysite.base.dj6.loading import get_app




class BaseMenuAdmin(CachingModel.Admin):
    app_menu = 'base'
    menu_group = 'base'


class UserAdmin(BaseMenuAdmin):
    query_fields = ["username","first_name"]
    menu_index = 101
    help_text = _(u'''新增本系统的用户，\"职员状态\"默认选中，如不选，用户将停用，不能登入系统！''')


class GroupAdmin(BaseMenuAdmin):
    menu_index = 100
    query_fields = ["name"]
    disabled_perms =["delete_group"]
    help_text = _(u'''角色是一组权限的集合，拥有该角色的用户将拥有该角色包含的所有权限,如要给用户分配角色，请到用户新增或编辑界面分配!<br/>浏览权限是每个模块的基本权限，所以选中非浏览权限外的其他权限，浏览权限会默认选中。''')


class PermissionAdmin(BaseMenuAdmin):
    menu_index = 100
    visible = False

Group.Admin = GroupAdmin
User.Admin = UserAdmin
Permission.Admin = PermissionAdmin


class _delete(Operation):
    help_text = _(u"删除选定记录")
    verbose_name = _(u"删除")

    def action(self):
        req = get_current_request()
        if req.user and req.user.pk == self.object.pk:
            raise Exception(u"%s" % _(u"当前用户不能删除自己."))
        if self.object.pk == 1:
            raise Exception(u"%s" % _(u"系统管理员不能被删除."))
        else:
            self.object.delete()


class _GroupDel(Operation):
    help_text = _(u"删除选定记录")
    verbose_name = _(u"删除")

    def action(self):
        if len(User.objects.filter(groups=self.object)) > 0:
            raise Exception(u'该角色正在使用,不能删除')
        else:
            self.object.delete()



@staticmethod
def clear():
    for e in User.objects.all():
        if e.pk != 1 and e.username != "employee":
            e.delete()


@staticmethod
def clear_group():
    for e in Group.objects.all():
        if e.pk != 1 and e.name != "role_for_employee":
            e.delete() 
    

def get_user_template(self):
    user_obj = self
    # User.objects.all()
    if user_obj:
        t9 = OperatorTemplate.objects.filter(user=user_obj, fpversion=9)
        t10 = OperatorTemplate.objects.filter(user=user_obj, fpversion=10)
    if len(t10) >= len(t9):
        return _(u"%(f)s ") % {'f': len(t10)}
    else:
        return _(u"%(f)s ") % {'f': len(t9)}


# 重载用户的get和filter查询
class ZUserManager(UserManager):
    def __init__(self):
        super(ZUserManager, self).__init__()
        self.contribute_to_class(User, 'objects')
    
    def get_query_set(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        qs = super(ZUserManager, self).get_query_set()
        try:
            req = get_current_request()
            if not req.session.has_key("employee") and not req.user.is_anonymous():
                qs = qs.exclude(username__exact="employee")
        except:
            pass
        return qs

    def get(self, *args, **kwargs):
        return super(ZUserManager, self).get(*args, **kwargs)


class ZGroupManager(db_models.Manager):
    def __init__(self):
        super(ZGroupManager, self).__init__()
        self.contribute_to_class(Group,'objects')
    
    def get_query_set(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        qs = super(ZGroupManager, self).get_query_set()
        try:
            req = get_current_request()
            if not req.session.has_key("employee") and not req.user.is_anonymous():
                qs = qs.exclude(name__exact="role_for_employee")
        except:
            pass
        return qs

    def get(self, *args, **kwargs):
        return super(ZGroupManager, self).get(*args, **kwargs)

User._delete = _delete
User.get_user_template = get_user_template
User.clear = clear
User._meta.verbose_name = _(u"用户")
Group._delete = _GroupDel
Group._meta.verbose_name = _(u"角色")
Group.clear = clear_group


def get_all_app_and_models(hide_visible_false=True, trans_apps=[]):
    lng = get_language()
    usr = threadlocals.get_current_user()
    if hide_visible_false:
        cache_key = "%s_%s_%s" % (lng, usr.username, "menu_list")
    else:
        cache_key = "%s_%s_%s" % (lng, usr.username, "menu_list_with_hide")
    if usr.is_anonymous():
        cache.delete(cache_key)
    menu_list = cache.get(cache_key)
    if menu_list:
        return menu_list
    apps = {}
    tmp_apps = [e for e in settings.INSTALLED_APPS]
    if trans_apps:
        tmp_apps = trans_apps
    for application in tmp_apps:
        app_label = application.split(".")[-1]
        apps[app_label] = {
            'models': [],
            'is_app_true': 'true'
            }
    for app_label in apps.keys():
        print("==========appskey=", app_label, "==", apps[app_label])
        app=get_app(app_label)
        print("==========typeofapp=", type(app))
        apps[app_label]['name'] = u"%(name)s" % {'name': hasattr(app, "verbose_name") and app.verbose_name or unicode(DataTranslation.get_field_display(ContentType, 'app_label', app_label))}
        apps[app_label]['index'] = hasattr(app, '_menu_index') and app._menu_index or 9999
        for i in dir(app):
            print("==========i=", i)
            app_menu = None
            try:
                model = app.__getattribute__(i)
                m0 = {}
                if issubclass(model, models.Model) and (model._meta.app_label==app_label):
                    admin = hasattr(model, "Admin") and model.Admin or None
                    if not model._meta.abstract:
                        perm = '%s.%s_%s' % (model._meta.app_label, "browse", model.__name__.lower())
                        if usr.has_perm(perm):
                            m0 = {'verbose_name': u"%(name)s"%{'name':model._meta.verbose_name},'model':model, 'index':9999}
                            if (not admin or not hasattr(admin, "visible") or admin.visible):
                                m0["visible"] = True
                            else:
                                m0["visible"] = False
                            if hasattr(admin, "menu_index"):
                                m0['index'] = admin.menu_index
                            
                            if hasattr(admin, "parent_model"):
                                m0["parent_model"]=admin.parent_model
                            if hasattr(admin,"select_related_perms"):
                                m0["select_related_perms"]=admin.select_related_perms
                            if hasattr(admin,"hide_perms"):
                                m0["hide_perms"]=admin.hide_perms
                            if hasattr(admin,"cancel_perms"):
                                m0["cancel_perms"]=admin.cancel_perms
                            app_menu=app_label
                            if hasattr(admin, "app_menu"):
                                app_menu=admin.app_menu
                            
                            m0['menu_group'] = hasattr(admin, "menu_group") and admin.menu_group or app_label#未配置时取app_menu（即app_label)
                            
                elif issubclass(model, AppOperation) and hasattr(model, 'view'):
                    operation_flag=hasattr(model,'operation_flag') and model.operation_flag or "true"
                    menu_group = hasattr(model, '_menu_group') and model._menu_group or app_label#未配置时取app_menu（即app_label)
                    if usr.has_perm("contenttypes.can_%s"%model.__name__):
                        m0={'verbose_name':u"%(name)s"%{'name': hasattr(model, "verbose_name") and model.verbose_name or (u"%s"%_(model.__name__))},
                            'model':None,
                            'operation': model,
                            'menu_group': menu_group,
                            'operation_flag':operation_flag,
                            'url': reverse(model.view.im_func),
                            'index': 9999}
                        if (not hasattr(model, 'visible') or getattr(model,'visible')):
                            m0["visible"]=True
                        else:
                            m0["visible"]=False
                        if hasattr(model, 'add_model_permission'):
                            m0["add_model_permission"]=model.add_model_permission
                        if hasattr(model, '_parent_model'):
                            m0["parent_model"]=model._parent_model
                        if hasattr(model, "_menu_index"):
                            m0['index']=model._menu_index
                        if hasattr(model,"_select_related_perms"):
                            m0["select_related_perms"]=model._select_related_perms
                        if hasattr(model,"_hide_perms"):
                            m0["hide_perms"]=model._hide_perms
                        if hasattr(model,"_cancel_perms"):
                            m0["cancel_perms"]=model._cancel_perms
                            
                        app_menu=app_label
                        if hasattr(model, "_app_menu"):
                            app_menu=model._app_menu
                              
                elif issubclass(model, AppPage):
                    app_menu = hasattr(model, 'app_menu') and model.app_menu or app_label
                    menu_group = app_menu
                    if  usr.has_perm("contenttypes.can_%s"%model.__name__) or (not model.visible and not hide_visible_false):
                        m0={'verbose_name':u"%(name)s"%{'name': hasattr(model, "verbose_name") and model.verbose_name or (u"%s"%_(model.__name__))},
                            'model':None,
                            'page': model,
                            'operation': model,
                            'menu_group': menu_group,
                            'url': '/page/%s/%s/'%(menu_group,model.__name__),#reverse(model.view.im_func),
                            'index': model.menu_index,
                            'visible':model.visible
                            }
                        
                if m0:
                    m0['app_label']=app_label
                    m0['name']=u"%(name)s"%{'name':model.__name__}
                    if app_menu not in apps: apps[app_menu]={
                        'name':u"%(name)s"%{'name':_(app_menu)},
                        'models': [m0,],
                        'index': hasattr(app, '_menu_index') and app._menu_index or 9999
                        }
                    else:
                        apps[app_menu]['models'].append(m0)
            except TypeError:
                pass
            except:
                import traceback; traceback.print_exc()
                pass
    if hide_visible_false:
        for k,v in apps.items():
            vmodels=[m for m in v['models'] if m["visible"]]
            v['models']=vmodels
    mlist=[(k,v) for k,v in apps.items() if v['models']]
    mlist.sort(lambda x1,x2: x1[1]['index']-x2[1]['index'])
    for m in mlist: 
        m[1]['models'].sort(lambda x1,x2: (x1['index']-x2['index']) or (x1['name']>=x2['name'] and 1 or -1))
    #return dict(mlist)不能排序
    cache.set(cache_key,mlist,60*60*24)
    
    return mlist


def get_app_label_from_app(app):
    plist = app.__name__.split('.')
    if len(plist)==3:
        return plist[1]
    elif len(plist)==2:
        return plist[0]
    else:
        return None

def get_model_or_AppOperation_class_from_app(app):
    '''
    获取所有 model AppOperation 类对象
    [(app_label,class), ]
    '''
    from django.db import models
    ret = []
    label = get_app_label_from_app(app)
    for i in dir(app):
        try:
            model=app.__getattribute__(i)
            if issubclass(model, AppOperation) and hasattr(model, 'view') and not hasattr(model, '_parent_model'):
                ret.append((label,model))
            if issubclass(model, AppPage):
                ret.append((label,model))
            elif issubclass(model, models.Model) and (model._meta.app_label==label):
                ret.append((label,model))
        except TypeError:
            pass
        except:
            import traceback; traceback.print_exc()
            pass
    return ret

def permission_unicode(self):
    return _("%(name)s")%{'name':_(self.name)}

def get_all_permissions(queryset=None):
        appss=get_all_app_and_models()
        apps=dict(appss)
        empty_app=[]
        change_operation_menu=[]
        Permission.__unicode__=permission_unicode
        if queryset==None: queryset=Permission.objects.all()
        for app_index in apps:
                empty_models=[]
                app_models=apps[app_index]['models']
                for model in app_models:
                        m=model['model']
                        admin=hasattr(m, "Admin") and m.Admin or None
                        disabled_perm=[]
                        if admin:
                                if hasattr(admin,"disabled_perms"):
                                    disabled_perm=admin.disabled_perms
                        elif hasattr(model["operation"],"_disabled_perms"):
                                disabled_perm=model["operation"]._disabled_perms
                        permissions=[]
                        if m==None:
                                ct = ContentType.objects.filter(app_label=app_index, model=model['operation'].__name__.lower()) 
                                code_name='can_%s'%model['operation'].__name__
                                for perm in queryset.filter(content_type=ct):
                                    if perm.codename not in disabled_perm:
                                            permissions.append(perm)
                                if model.has_key("add_model_permission"):
                                        for  elem in model["add_model_permission"]:
                                            ct=ContentType.objects.get_for_model(elem)
                                            for perm in queryset.filter(content_type=ct):
                                                        if perm.codename not in disabled_perm:
                                                                permissions.append(perm)
                        else:
                                ct=ContentType.objects.get_for_model(m)                             
                                for perm in queryset.filter(content_type=ct):
                                        if perm.codename not in disabled_perm:
                                                permissions.append(perm)
                        if permissions:        
                                model['permissions']=permissions
                        else:
                                empty_models.append(model)
                for m in empty_models: app_models.remove(m)
                if len(app_models)==0:
                        empty_app.append(app_index)
        for app_index in empty_app: apps.pop(app_index)
        for elem in change_operation_menu:#elem->["app_menu.model",perm] 
            elem_app,elem_model=elem[0].split(".",1)#必须为模型名，不能为权限的名字
            try:
                for e in dict(apps)[elem_app]["models"]:
                    if e["name"]==elem_model:
                        e["permissions"].append(elem[1])
            except:
                from traceback import print_exc
                #print_exc()
        mlist=apps.items()
        mlist.sort(lambda x1,x2: x1[1]['index']-x2[1]['index'])
        return  mlist

