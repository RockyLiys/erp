#coding=utf-8
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.auth.decorators import permission_required
import dataviewdb, views, data_edit
import viewmodels
import dataoperation
import importandexport
from django.core.urlresolvers import reverse
from modelutils import setview,advance_query_index

from base import base_code

from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.db.models import Q
from datalist import data_list, data_demo



urlpatterns = patterns('',
    (r'^import/get_import$', importandexport.get_importPara),
    (r'^import/file_import$', importandexport.file_import),

    (r'^list/(?P<fn>.*)/$', data_list),
    (r'^data_demo/', data_demo),    
    (r'^index/$', dataviewdb.mydesktop),
    (r'^system/help/$', dataviewdb.sys_help),
    (r'^set_option$', dataviewdb.set_option),

    (r'^(?P<app_label>[^/]*)/$',dataviewdb.myapp),
    (r'^BaseCode/category/', base_code.get_category),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/$', dataviewdb.DataList),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/_new_/$', data_edit.DataNew),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/(?P<DataKey>[^/]*)/$', data_edit.DataDetail),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/choice_data_widget$', views.get_chioce_data_widget),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/_op_/(?P<op_name>[^/]*)/$', dataoperation.get_form),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/query/show$', advance_query_index),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/view/show$', setview),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/view$', viewmodels.save_view),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/view/(?P<view_name>[^/]*)$', viewmodels.get_view),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/view/(?P<view_name>[^/]*)/delete$', viewmodels.delete_view),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/import/show_import$', importandexport.show_import),

    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/export/show_export$', importandexport.show_export),
    (r'^(?P<app_label>[^/]*)/(?P<model_name>[^/]*)/export/file_export$', importandexport.file_export),

    (r'^BackupDBValidate/(?P<type>[^/]*)$', views.backup_db_validate), #备份数据库的有效性验证，如验证在当前时间的一个小时内只能备份一次数据库
    (r'^getBackupsched$', views.getBackupsched),
    (r'^init_db$', views.init_db),
    (r'^option$', views.user_option),
    (r'^sys_option$', views.sys_option),
    (r'^restore_db$', views.restore_db),
    (r'^get_init_db_data',views.get_init_db_data),
    (r'^update_process',views.update_process),#更新备份数据库后的状态
    (r'^get_import_progress',importandexport.detailprogress),
    (r'^check_update_file$', views.check_update_file),#检查上传文件
)

dbapp_url=settings.UNIT_URL+"data/"#"/".join(reverse(views.init_db).split('/')[:-1])+'/'
surl=settings.UNIT_URL[1:]

def get_model_new_url(model):
        return reverse(data_edit.DataNew, args=(model._meta.app_label, model.__name__))

def get_model_data_url(model):
        return reverse(dataviewdb.DataList, args=(model._meta.app_label, model.__name__))

def get_obj_url(obj):
        return reverse(data_edit.DataDetail, args=(obj._meta.app_label, obj.__class__.__name__, obj.pk))


