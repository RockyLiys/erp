#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible
import datetime

from mysite.base import *
from mysite.base.middleware import threadlocals
from mysite.base.operation import OperationBase, Operation, ModelOperation
from mysite.base.modeladmin import ModelAdmin, CACHE_EXPIRE
from mysite.base.models_addition import AdditionData
from mysite.base.models_logentry import LogEntry, ADDITION, DELETION, CHANGE

# from mysite.base.sync_hook import delete_hook, save_hook

force_unicode = str

CACHE_PREFIX = settings.CACHE_MIDDLEWARE_KEY_PREFIX


def cache_key(model, id):
    return ('%s_DBC:%s:%s' % (CACHE_PREFIX, model._meta.db_table, id)).replace(' ', '_')


class RowCacheManager(models.Manager):
    """Manager for caching single-row queries. To make invalidation easy,
    we use an extra layer of indirection. The query arguments are used as a
    cache key, whose stored value is the unique cache key pointing to the
    object. When a model using RowCacheManager is saved, this unique cache
    should be invalidated. Doing two memcached queries is still much faster
    than fetching from the database."""

    def get(self, *args, **kwargs):
        # import traceback; traceback.#print_stack(limit=4)
        if not self.model.Admin.cache:
            return super(RowCacheManager, self).get(*args, **kwargs)
        if 'johnny.middleware.QueryCacheMiddleware' in settings.MIDDLEWARE_CLASSES:  # 已经实现了缓存功能
            return super(RowCacheManager, self).get(*args, **kwargs)
        id = repr(kwargs)
        pointer_key = cache_key(self.model, id)
        try:
            model_key = cache.get(pointer_key)
        except UnicodeDecodeError:
            pointer_key = cache_key(self.model, id.decode("utf-8"))
            model_key = cache.get(pointer_key)
        if model_key is not None:
            model = cache.get(model_key)
            if model is not None:
                # print "\tget in cache, %s->%s"%(pointer_key, model_key)
                return model
        # One of the cache queries missed, so we have to get the object from the database:
        # print "not in cache"
        model = super(RowCacheManager, self).get(*args, **kwargs)
        cache_expire = int(self.model.Admin.cache)
        if cache_expire < 10: cache_expire = CACHE_EXPIRE
        model_key = cache_key(model, model.pk)
        cache.set(pointer_key, model_key, cache_expire)
        # print "\tset_cache1: %s->%s"%(pointer_key, model_key)
        try:
            cache.set(model_key, model, cache_expire)
            # print "\tset_cache2: %s->%s,%s"%(model_key, model.pk, model)
        except:
            # print model_key, model, model.__class__
            # import traceback; traceback.#print_exc()
            pass
        return model

    def get_query_set(self):
        qs = super(RowCacheManager, self).get_query_set()
        try:  # 根据 status 排除已经删除/停用的数据
            if hasattr(self.model, "can_restore") and self.model.can_restore:
                qs = qs.exclude(status=STATUS_INVALID)
                pass  # 修改已删除人员历史记录显示为空的问题
            else:
                qs = qs.exclude(status=STATUS_STOP).exclude(status=STATUS_INVALID)
        except:
            pass

        op = threadlocals.get_current_user()
        if (op is None) or op.is_anonymous():
            return qs
        if not hasattr(op, "customer_id"): return qs

        # TODO: 根据当前用户的权限过滤数据
        # 根据登录用户所属客户，过滤出该客户的数据
        if hasattr(qs.model, "customer"):
            qs = qs.filter(customer_id=op.customer_id)
        return qs


ModelBase = type(models.Model)


class MetaCaching(ModelBase):
    """Sets ``objects'' on any model that inherits from CachingModel to
    be a RowCacheManager. This is tightly coupled to Django internals, so it
    could break if you upgrade Django. This was done partially as a proof-of-
    concept. It is advised to only use code above the comment line."""

    def __new__(*args, **kwargs):
        new_class = ModelBase.__new__(*args, **kwargs)
        new_manager = RowCacheManager()
        new_manager.contribute_to_class(new_class, 'objects')
        new_class._default_manager = new_manager
        return new_class


@python_2_unicode_compatible
class CachingModel(models.Model, OperationBase):
    change_operator = models.CharField(verbose_name=_(u'修改者'), max_length=30, null=True, editable=False)  # who last modify
    change_time = models.DateTimeField(verbose_name=_(u'修改时间'), auto_now=True, editable=False, null=True)
    create_operator = models.CharField(verbose_name=_(u'创建者'), max_length=30, null=True, editable=False)  # who create this object
    create_time = models.DateTimeField(verbose_name=_(u'创建时间'), editable=False, null=True)
    delete_operator = models.CharField(verbose_name=_(u'删除者'), max_length=30, null=True, editable=False)  # who delete this object
    delete_time = models.DateTimeField(verbose_name=_(u'删除时间'), editable=False, null=True)
    status = models.SmallIntegerField(verbose_name=_(u'状态'), default=STATUS_OK, editable=False, null=False)
    all_objects = models.Manager()

    def get_addition_field(self, key):
        try:
            content_type_id = ContentType.objects.get_for_model(self).pk
            a = AdditionData.objects.get(content_type=content_type_id, object_id=self.pk, key=key, delete_time__isnull=True)
            if a.data:  return a.data
            return a.value
        except:
            raise
            return None

    def delete_addition_field(self, key):
        content_type_id = ContentType.objects.get_for_model(self).pk
        try:
            a = AdditionData.objects.get(content_type=content_type_id, object_id=self.pk, key=key, delete_time__isnull=True)
            a.delete_time = datetime.datetime.now()
            a.save()
        except:
            pass
        return content_type_id

    def set_addition_field(self, key, value):
        cid = self.delete_addition_field(key)
        AdditionData(content_type_id=cid, object_id=self.pk, key=key, value=value).save()

    def set_addition_data_field(self, key, data):
        cid = self.delete_addition_field(key)
        AdditionData(content_type_id=cid, object_id=self.pk, key=key, data=data).save()

    class Admin(ModelAdmin):
        pass

    class _clear(ModelOperation):
        help_text = _(u"清空所有记录")  # 清除该表的全部记录
        verbose_name = u"清空记录"

        def action(self):
            self.model.objects.all().delete()

    class _add(ModelOperation):
        help_text = _(u"新增记录")  # 新增记录
        verbose_name = _(u"新增")

        def action(self):
            pass

    class _delete(Operation):
        help_text = _(u"删除选定记录")  # 删除选定的记录
        verbose_name = _(u"删除")

        def action(self):
            self.object.delete()

    class _change(Operation):
        help_text = _(u"修改选定记录")
        verbose_name = _(u"修改")
        confirm = ""
        only_one_object = True

        def action(self):
            pass

    class dataexport(Operation):
        help_text = _(u"数据导出")  # 导出
        verbose_name = _(u"导出")
        visible = False

        def action(self):
            pass

    class View_detail(Operation):
        help_text = _(u"查看详情")
        verbose_name = _(u"详情")
        only_one_object = True

        def action(self):
            pass

    class dataimport(Operation):
        help_text = _(u"导入数据")  # 导入
        verbose_name = u"导入"
        visible = False

        def action(self):
            pass

    class view(Operation):
        help_text = _(u"自定义视图")  # 视图
        verbose_name = u"自定义视图"
        visible = False

        def action(self):
            pass

    def save(self, *args, **kwargs):
        is_new = False
        if self.pk == None or self.create_time == None:
            is_new = True
        elif kwargs.get("force_insert", False):
            is_new = True
        if is_new and kwargs.get("force_update", False):
            is_new = False
        log_msg = kwargs.get('log_msg', True)  # 默认为True
        print(
            "save: is_new=%s, self.pk=%s, self.create_time=%s, kwarg=%s" % (is_new, self.pk, self.create_time, kwargs))
        op = threadlocals.get_current_user()
        if op and op.is_anonymous():
            op = None
        print("save: %s self.status:%s" % (self.__class__.__name__, self.status))
        if is_new:
            self.create_time = datetime.datetime.now()
            if op: self.create_operator = op.username
            old_obj = None
        else:
            if self.status == STATUS_INVALID:  # 标记为删除
                self.delete_time = datetime.datetime.now()
                if op: self.delete_operator = op.username
            else:  # 修改
                self.change_time = datetime.datetime.now()
                if op: self.change_operator = op.username
            # pwp添加具体的修改信息

            old_obj = self.__class__.all_objects.filter(pk=self.pk)[0]
            change_info = []
            for field in old_obj._meta.fields:
                field_name = field.name
                if field_name == 'status' or field_name not in [abs_field.name for abs_field in
                                                                CachingModel._meta.fields]:  # 只显示非自动维护字段的改变
                    if field.choices:
                        old_value = (old_obj.__getattribute__("get_" + field_name + "_display")()) or ""
                        new_value = (self.__getattribute__("get_" + field_name + "_display")()) or ""
                    else:
                        old_value = getattr(old_obj, field_name)
                        new_value = getattr(self, field_name)

                    if new_value != old_value and (old_value or "None") != (new_value or "None"):
                        change_info.append(u"%s(%s->%s)" % (field.verbose_name, old_value or "", new_value or ""))

            if kwargs.has_key('log_msg') and type(kwargs['log_msg']) != bool:  # 配置了指定写入的日志信息(默认写入)
                kwargs['log_msg'] = u"%s" % kwargs['log_msg']  # + u";".join(change_info)
            elif change_info:
                kwargs['log_msg'] = u";".join(change_info)
            elif self.status != STATUS_INVALID:  # 不是删除操作
                return  # 没有修改任何数据，无须进行保存操作

        log_msg_content = kwargs.pop('log_msg', '')
        invalidate_cache = kwargs.pop('invalidate_cache', True)
        # print "save: %s, super save: %s"%(self.__class__.__name__,self.__dict__)

        # if SYNC_MODEL:
        #     hk = save_hook(is_new,self,old_obj).check()
        # super(CachingModel, self).save(*args, **kwargs)
        # if SYNC_MODEL:
        #     hk.sync()
        if self.Admin.cache and invalidate_cache:
            key = cache_key(self, self.pk)
            #                    print "\tinvalidate_cache:", key
            cache.delete(key)
        if log_msg or (self.Admin.log and log_msg != False):  # log_msg设置了字符串，无论Admin.log都写日志；log_msg=False 表示强制不写日志

            LogEntry.objects.log_action(
                user_id=op and op.pk or None,
                content_type_id=ContentType.objects.get_for_model(self).pk,
                object_id=self.pk,
                object_repr=force_unicode(self),
                action_flag=(is_new and ADDITION) or (self.status == STATUS_INVALID) and DELETION or CHANGE,
                change_message=log_msg_content[0:511] or ""
            )
        if is_new:
            try:
                for r in self._meta.get_all_related_objects():
                    if isinstance(r.field, models.OneToOneField):
                        r.model(**{r.field.name: self}).save()
            except:
                pass

    def data_valid(self, sendtype=SAVETYPE_NEW):  # 数据的业务逻辑处理函数,sendtype表示是1:新增，2:修改
        pass

    def delete_(self):
        self.status = STATUS_INVALID

        # if SYNC_MODEL:
        #     hk = save_hook(is_new,self,old_obj).check()
        # super(CachingModel, self).save()
        # if SYNC_MODEL:
        #     hk.sync()

    def delete(self):
        if self.Admin.cache:
            key = cache_key(self, self.pk)
            cache.set(key, None)
            cache.delete(key)
            print('------CachingModel delete: %s---------' % key)
        if self.Admin.log:
            op = threadlocals.get_current_user()
            if op and op.is_anonymous(): op = None
            LogEntry.objects.log_action(
                user_id=op and op.pk or None,
                content_type_id=ContentType.objects.get_for_model(self).pk,
                object_id=self.pk,
                object_repr=force_unicode(self),
                action_flag=DELETION
            )
        super(CachingModel, self).delete()
        # if SYNC_MODEL:
        #     delete_hook(self)

    class Meta:
        abstract = True
        ordering = ['-change_time']

    __metaclass__ = MetaCaching
