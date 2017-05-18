#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django import forms

from mysite.base.base_code import base_code_by
from mysite.base.cached_model import CachingModel
from mysite.base.models_bak import is_parent_model

User._menu_index = 400
Permission._visible = False


class RoleObjectProperty(CachingModel):
    """
    定义一个角色对其主体对象及其从属对象的属性（字段）的可访问性：改变、搜索、浏览/查看
    注意，为简化用户操作起见，一个角色如果没有对一个对象定义属性的可访问性，则具有全部属性的全部访问权限
    """
    role = models.ForeignKey("Role")
    change = models.BooleanField(_(u'能改变自己的财产'))
    view = models.BooleanField(_(u'可以查看该财产'))
    search = models.BooleanField(_(u'可以搜索的财产'))
    object_type = models.ForeignKey(ContentType, verbose_name=_(u'这个对象类型'), blank=True, null=True)  # 主体对象或从属对象
    property = models.CharField(_(u'财产,或者为对象'), max_length=40)  # 一个对象的属性名称

    class Admin(CachingModel.Admin):
        visible = False

    def __unicode__(self):
        return u"%s, %s.%s" % (self.role, self.object_type, self.property)

    def limit_object_type_to(self, queryset):
        # 限制对象类型只能是 角色的主体对象及其从属对象

        if not self.role: return queryset
        qs = []
        model = self.role.object_type.model_class()
        for ct in queryset:
            if is_parent_model(model, ct.model_class()):
                qs.append(ct.id)
        return queryset.filter(id__in=qs)


# 注：当前没有用到该模型，菜单上的【角色】，实际上是Group表，请直接参考django-darcy20110510
class Role(CachingModel):
    """
    定义主体对象类型上的角色及其权限范围
    例如，以部门表为主体对象类型，可以定义该部门下的“超级管理员”、“部门经理”、“人事管理员”、“考勤机管理员”等等
    这些管理员的操作权限都会被限定在一个特定部门内，主体对象的意思是这个对象所有的从属对象也会受到限制，比如由于员工对象属于特定的部门，因此某一角色的用户在对员工进行操作时，其权限也会限定在该部门的范围内
    """
    object_type = models.ForeignKey(ContentType, blank=True, null=True)
    name = models.CharField(_(u'角色名称'), max_length=40, blank=False, null=False)
    permissions = models.ManyToManyField(Permission, verbose_name=_(u'权限'))

    class Admin(CachingModel.Admin):
        menu_index = 400
        children = [RoleObjectProperty, ]

    def __unicode__(self):
        return _("%(name)s for %(type)s") % {'name': self.name, 'type': self.object_type}

    def limit_permissions_to(self, queryset=None):
        # 限制对象类型只能是 角色的主体对象及其从属对象

        if not self.object_type: return queryset
        qs = []
        if not queryset: queryset = Permission.objects.all()
        model = self.object_type.model_class()
        for perm in queryset:
            m = perm.content_type.model_class()
            if m and is_parent_model(model, m):
                qs.append(perm.id)
        return queryset.filter(id__in=qs)

    class Meta:
        verbose_name = _(u"角色")


class UserRole(CachingModel):
    """定义用户在某些对象上的角色"""
    user = models.ForeignKey(User, related_name="userroleuser")
    objects_filter = models.CharField(max_length=200)  # 对象查询条件，用户在满足该查询条件的对象上才具有指定角色
    role = models.ForeignKey(Role)

    class Admin(CachingModel.Admin):
        visible = False


def get_browse_fields(model, user, search=False):
    '''
    API
    查询一个用户user可以浏览/查看模型model的那些字段
    '''
    fields = []
    ct = ContentType.objects.get_for_model(model)
    for ur in user_role.objects.filter(user=user):  # 检查该用户的所有角色
        rfs = role_object_property.objects.filter(role=ur.role, object_type=ct)  # 检查该角色的所有对象属性可见性
        if rfs.count():  # 定义过该角色对该对象类型的可访问性
            if search:
                fields.append([r.property for r in rfs if r.search])
            else:
                fields.append([r.property for r in rfs if r.view])
        else:  # 没有定义过可访问性,则检查该对象类型的所有者类型
            m = is_parent_model(ur.role.object_type.model_class(), model)
            if m: fields.append(m._meta.get_all_field_names())
    return tuple(fields)


def get_search_fields(model, user):
    '''
    API
    查询用户user可以搜索一个模型的那些字段
    '''
    return get_browse_fields(model, user, "search")


def is_obj_owner(model, id, obj):
    if isinstance(obj, model):
        return id == obj.pk
    for f in obj._meta.fields:
        if isinstance(f, models.fields.related.ForeignKey):
            ret = is_obj_owner(model, id, getattr(obj, f.name))
            if ret: return ret
            if ret == False: return ret
    return None


def get_change_fields(obj, user):
    '''
    API 查询用户user可以编辑/改变obj一个对象的那些字段
    '''
    fields = []
    ct = ContentType.objects.get_for_model(obj.__class__)
    for ur in user_role.objects.filter(user=user):  # 检查该用户的所有角色
        if is_owner(ur.role.object_type.model, ur.object_id, obj):  # 检查用户是否对拥有该对象的主体对象具有某种角色
            rfs = role_object_property.objects.filter(role=ur.role, object_type=ct)  # 检查该角色的所有对象属性可见性
            if rfs.count():  # 定义过对该对象类型的可访问性
                fields.append([r.property for r in rfs if r.change])
            else:  # 没有定义过可访问性,则该对象的全部属性可用
                fields.append(obj._meta.get_all_field_names())
    return tuple(fields)


def model_owner_rel_(model, id, obj, obj_id=""):
    # print "model_owner_rel", obj, obj_id
    if obj == model:
        return obj_id + ("pk==%s" % id)
    for f in obj._meta.fields:
        if isinstance(f, models.fields.related.ForeignKey):
            # print "ForeignKey: ", f.name
            ret = model_owner_rel(model, id, f.rel.to, obj_id=obj_id + f.name + "__")
            if ret: return ret
    return None


def model_owner_rel(parent_model, model, obj_id=""):
    # print "model_owner_rel", parent_model, obj_id
    if parent_model == model:
        return obj_id + "pk"
    for rel in parent_model._meta.get_all_related_objects():
        # print obj_id, "ForeignKey: ", rel.model, rel.field.name
        ret = model_owner_rel(rel.model, model, obj_id=obj_id + rel.field.name + "__")
        if ret: return ret
    return None


def filter_data_by_user(query_set, user):
    '''
    API
    根据用户user的角色权限对记录集query_set进行过滤，返回过滤后的记录集
    '''
    model = query_set.model
    q = models.Q(pk__in=[])
    for ur in user_role.objects.filter(user=user):  # 检查该用户的所有角色
        f = model_owner_rel(ur.role.object_type.model, model)  # 得到该角色对应的对象数据查询条件
        if f:
            q |= models.Q(**{f: ur.object_id})
    return query_set.filter(q)


def filter_data_by_user_and_perm(query_set, user, perm):
    '''
    API 根据用户user的角色和权限对记录集query_set进行过滤，返回其中用户具有perm权限的记录集
    '''
    model = query_set.model
    ct = ContentType.objects.get_for_model(model)
    if isinstance(perm, Permission):
        p = perm
    else:
        p = Permission.get(content_type=ct, codename=perm)
    q = models.Q(pk__in=[])
    for ur in user_role.objects.filter(user=user):  # 检查该用户的所有角色
        if p in ur.role.permissions.all():
            f = model_owner_rel(ur.role.object_type.model, model)  # 得到该角色对应的对象数据查询条件
            if f:
                q |= models.Q(**{f: ur.object_id})
    return query_set.filter(q)
