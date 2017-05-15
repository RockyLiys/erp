#coding=utf-8
from django.template import loader, RequestContext, Template, TemplateDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
from exceptions import AttributeError
import string
import datetime
from utils import *
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django import forms
from django.utils.encoding import smart_str
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from datautils import *
from django.utils.datastructures import SortedDict
from modelutils import getDefaultJsonDataTemplate,getUsrCreateFrameOptions,GetModel
from datautils import get_model_master
import django.dispatch
import widgets
from enquiry import Enquiry
from base.operation import OperationBase, Operation, ModelOperation
from base.cached_model import STATUS_INVALID
from dbapp.templatetags import dbapp_tags
from traceback import print_exc
from django.db import models
from base.cached_model import SAVETYPE_NEW,SAVETYPE_EDIT

try:
    import cPickle as pickle
except:
    import pickle

def make_instance_save(instance, fields, fail_message):
    """Returns the save() method for a Form."""
    def save(self, commit=True):
            return forms.save_instance(self, instance, fields, fail_message, commit)
    return save

def make_instance_data_valid(instance, fields):
    """Returns the data_valid() method for a Form."""
    from django.forms.models import   construct_instance
    def data_valid(self,sendtype):        
            obj= construct_instance(self, instance, fields)
            if hasattr(obj,"data_valid"):
                return obj.data_valid(sendtype)
            else:
                pass
    return data_valid

def _form_for_model(model, instance=None, form=forms.BaseForm, fields=None, post=None,
               formfield_callback=widgets.form_field, lock_fields=[], read_only=False,level_type=0): 
    if hasattr(model.Admin, "form_class"):
            if model.Admin.form_class:
                    return model.Admin.form_class(post, instance=instance)
    opts = model._meta 
    field_list = []
    default_widgets={}
    if hasattr(model.Admin, "default_widgets"):
            default_widgets=model.Admin.default_widgets
            if callable(default_widgets): default_widgets(instance)
    for f in opts.fields + opts.many_to_many: 
            if not f.editable: 
               continue 
            if fields and not f.name in fields: 
               continue
#            if post and not f.name in post.keys(): 
#                continue

            current_value = None
            #print "////f=",f
            if instance: 
                    try:
                            current_value=f.value_from_object(instance)
                            if isinstance(f,models.BooleanField):
                                if current_value:
                                    current_value=1
                                else:
                                    current_value=0
                    except ValueError:
                            pass
            elif f.has_default and not (f.default==models.fields.NOT_PROVIDED):
                    current_value=f.default

            if read_only or f.name in lock_fields or \
                    (f.primary_key and current_value): #被锁定的字段不能被修改,主键不能被修改
                    formfield = widgets.form_field_readonly(f, initial=current_value)
            else:
                    widget=None
                    if f.name in default_widgets: 
                            widget=default_widgets[f.name]
                    elif f.__class__ in default_widgets:
                            widget=default_widgets[f.__class__]
                    if widget:
                            formfield = formfield_callback(f, initial=current_value, widget=widget)
                    else:
                            formfield = formfield_callback(f, initial=current_value)
                    if formfield: 
                        widgets.check_limit(f, model, formfield, instance,level_type)
            if formfield:
                    field_list.append((f.name, formfield))

    base_fields = SortedDict(field_list) 
    
    return type(opts.app_label+"_"+model.__name__+'_edit', (form,), 
            {'base_fields': base_fields, '_model': model, 
             'save': make_instance_save(instance or model(), fields, 'created'),
             'data_valid':make_instance_data_valid(instance or model(), fields),
            })(post)

def form_for_model(model, instance=None, form=forms.BaseForm, fields=None, post=None,
               formfield_callback=widgets.form_field, lock_fields=[], read_only=False,level_type=0): 
    import os
    f=_form_for_model(model, instance or model(), form, fields, post, formfield_callback, lock_fields, read_only,level_type)
    
    if hasattr(model.Admin, "help_text"):
            f.admin_help_text=model.Admin.help_text
    if instance and instance.pk:
            f.object_photo=dbapp_tags.thumbnail_url(instance)
    help_image="img/model/%s.%s.png"%(model._meta.app_label, model.__name__)
    if os.path.exists(settings.MEDIA_ROOT+help_image):
            f.admin_help_image=settings.MEDIA_URL+"/"+help_image
    return f

def form_for_instance(instance, form=forms.BaseForm, fields=None, post=None,
               formfield_callback=widgets.form_field, lock_fields=[], read_only=False,level_type=0): 
    return form_for_model(instance.__class__, instance, form, fields, post, 
               formfield_callback, lock_fields, read_only,level_type)

pre_detail_response = django.dispatch.Signal(providing_args=["dataModel", "key"])
    
def DataDetailResponse(request, dataModel, form, key=None, instance=None, **kargs):
    from urls import get_model_data_url, dbapp_url
    from django.db import models
    import base
    from django.contrib.contenttypes.models import ContentType
    if not kargs: kargs={}
    tmp_file=request.GET.get('_t',"%s.html"%form.__class__.__name__)
    kargs["dbapp_url"]=dbapp_url
    request.dbapp_url=dbapp_url
    kargs["form"]=form
    kargs["title"]=(u"%s"%dataModel._meta.verbose_name).capitalize()
    kargs["dataOpt"]=dataModel._meta
    kargs['model_name']=dataModel.__name__
    kargs['app']=dataModel._meta.app_label
    if issubclass(dataModel,models.Model):
        kargs["app_menu"]=hasattr(dataModel.Admin,"app_menu") and dataModel.Admin.app_menu or  dataModel._meta.app_label
    kargs["add"]=key==None
    kargs["instance"]=instance
    if key and issubclass(dataModel, base.models.CachingModel) and dataModel.Admin.log:
            try:
                    ct=ContentType.objects.get_for_model(dataModel)
                    kargs['log_url']=get_model_data_url(base.models.LogEntry)+("?content_type__id=%s&object_id=%s"%(ct.pk,key))
                    kargs['log_search']=("content_type__id=%s&object_id=%s"%(ct.pk,key))
            except:
                    print_exc()
    if hasattr(dataModel.Admin, "form_tabs"):
            kargs["tabs"]=dataModel.Admin.form_tabs
    if hasattr(dataModel.Admin, "form_before_response"):
        dataModel.Admin.form_before_response(request, kargs, key)
    kargs["position"] = hasattr(dataModel.Admin, "position") and dataModel.Admin.position or None
    pre_detail_response.send(sender=kargs, dataModel=dataModel, key=key)
    template_list = [tmp_file, dataModel._meta.app_label+"."+dataModel.__name__+'_edit.html',dataModel.__name__+'_edit.html','data_edit.html']
    return render_to_response(template_list, RequestContext(request,kargs),)        

def new_object(model, data):
    fd={}
    fields=[]
    obj=model()
    for field in data:
            value=data[field]
            if field.find("__"): field=field.split("__")[0]
            try:
                    f=model._meta.get_field(field)
            except:
                    continue
            if isinstance(f, models.fields.related.ForeignKey):
                    fd[str(field)+"_id"]=value
            else:
                    fd[str(field)]=value
            fields.append(field)
    for f,v in fd.items():
        if hasattr(obj, f): setattr(obj, f, v)
    return obj, fields

post_check = django.dispatch.Signal(providing_args=["oldObj", "newObj"])
pre_check = django.dispatch.Signal(providing_args=["oldObj", "model"])
post_change_check = django.dispatch.Signal(providing_args=["oldObj", "newObj"])

NON_FIELD_ERRORS = '__all__'
    
def save_for_files(request,instance):
    u"图片字段保存"
    import datetime
    if request.FILES:
        for k,v in request.FILES.items():
            if hasattr(instance,k):
                getattr(instance,k).save(datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")+".jpg",v)
        #instance.save()
            
def DataNewPost(request, dataModel):
    from admin_detail_view import doPostAdmin,doCreateAdmin
    from django.db import IntegrityError 
    if dataModel==User:
            return doPostAdmin(request, dataModel, '_new_')

    f = form_for_model(dataModel, post=request.POST)
    if hasattr(dataModel.Admin, "form_post"):
        dataModel.Admin.form_post(request, f, None)
    if dataModel.__name__=="Group":
        if len(request.POST.get("permissions","")) == 0:
            info = _(u"请为该角色勾选权限！")
            f.errors[NON_FIELD_ERRORS]=u'<ul class="errorlist"><li>%s</li></ul>'%info 
            return DataDetailResponse(request, dataModel, f) 
        #print "//////////////////////",dir(request.POST)
        #print "//////////////////////",type(request.POST.get("permissions","")),"//",request.POST.get("permissions")
    if f.is_valid():
        obj=None
        key=(dataModel._meta.pk.name in f.cleaned_data) and f.cleaned_data[dataModel._meta.pk.name] or None
        if key:
                try:
                        obj=dataModel.objects.get(pk=key)
                        if not (fieldVerboseName(dataModel, "status") and obj.status==STATUS_INVALID):
                                f.errors[dataModel._meta.pk.name]=[_(u"复制")]
                                return DataDetailResponse(request, dataModel, f)
                except ObjectDoesNotExist:
                        print_exc()
                        pass
        oldEmp=None            
#        try:
#                oldEmp=dataModel.objByID(emp.id)
#        except: pass
#        
        try:
                pre_check.send(sender=request, model=dataModel, oldObj=oldEmp)
                f.data_valid(SAVETYPE_NEW)#进行业务逻辑处理
                #print "///////////before save=",dir(f)
                obj=f.save()
                save_for_files(request,obj)
                key=obj.pk
        except IntegrityError:
                if dataModel.__name__=="Group":
                    info = _(u"角色名称不能重复")
                else:
                    info =_(u"数据不能重复")
                f.errors[NON_FIELD_ERRORS]=u'<ul class="errorlist"><li>%s</li></ul>'%info
                return DataDetailResponse(request, dataModel, f)
        except Exception, e: #通常是不满足数据库的唯一性约束导致保存失败
                f.errors[NON_FIELD_ERRORS]=u'<ul class="errorlist"><li>%s</li></ul>'%e
                #print "data_edit,f.errors[NON_FIELD_ERRORS]=",f.errors[NON_FIELD_ERRORS]
                return DataDetailResponse(request, dataModel, f)
        if hasattr(dataModel.Admin, "form_after_save"):
            #print"====form_after_save"
            dataModel.Admin.form_after_save(request, oldEmp, obj)
        try:
            #print"====oldObj",oldEmp,"====newObj",obj.permissions_set
            post_check.send(sender=request, oldObj=oldEmp, newObj=obj)
        except:
            print_exc()

        popup = request.GET.get("_popup", "")
        if popup:
                the_add_object = unicode(obj)
                return HttpResponse(u'<script type="text/javascript">\nopener.dismissAddAnotherPopup(window, "%s", "%s");\n</script>' % (key, the_add_object))
        
        return HttpResponse('{ Info:"OK" }')
        
    else:
        for i,v in dict(f.errors).items(): 
            print i, ":"
            for vi in v: print "\t", vi
        f.errors[NON_FIELD_ERRORS]=u'<ul class="errorlist"><li>%s: %s</li></ul>' % (i, vi)
        return DataDetailResponse(request, dataModel, f)

@login_required        
def DataNew(request, app_label, model_name):
    from admin_detail_view import retUserForm,adminForm,doPostAdmin,doCreateAdmin
    try:
        dataModel=GetModel(app_label, model_name)
        lock=request.GET.get("_lock",None)
        read_only=lock=='ALL'
        if not hasPerm(request.user, dataModel, "add"):
                return NoPermissionResponse()
        if not dataModel: return NoFound404Response(request)
        if request.method=="POST" and not read_only:
                return DataNewPost(request, dataModel)

        instance,fields=new_object(dataModel, request.GET)
        if dataModel==User:
                return retUserForm(request, adminForm(request), isAdd=True)
        level_type = get_leveltype_byhttpreferer(request)
        dataForm = form_for_instance(instance, lock_fields=lock and fields or [], read_only=read_only,level_type=level_type)
        return DataDetailResponse(request, dataModel, dataForm, None, instance)
    except:
        import traceback;traceback.print_exc()

def DataChangePost(request, dataModel, dataForm, emp):
    f=dataForm
    if hasattr(dataModel.Admin, "form_post"):
        dataModel.Admin.form_post(request, f, emp)

    if f.is_valid():
        #检查有没有改变关键字段
        key=(dataModel._meta.pk.name in f.cleaned_data) and f.cleaned_data[dataModel._meta.pk.name] or emp.pk
        if key and "unicode" not in str(type(key)):
            key = unicode(key)
        if key and ('%s'%emp.pk)!=('%s'%key):
            f.errors[dataModel._meta.pk.name]=[_(u"关键字段%(object_name)s不能修改!")%{'object_name':fieldVerboseName(dataModel, dataModel._meta.pk.name)}];
            return DataDetailResponse(request, dataModel, f, key=emp.pk)
        obj=None
        for field in emp._meta.many_to_many:
            setattr(emp, field.name+"_set", tuple(getattr(emp, field.name).all()))

        obj_old_str=pickle.dumps(emp)
        obj_old=pickle.loads(obj_old_str)

        try:
            pre_check.send(sender=request, model=dataModel, oldObj=obj_old)
            f.data_valid(SAVETYPE_EDIT)#进行业务逻辑处理
            obj=f.save()
            save_for_files(request,obj)
        except Exception, e: #通常是不满足数据库的唯一性约束导致保存失败
            f.errors[NON_FIELD_ERRORS]=u'<ul class="errorlist"><li>%s</li></ul>'%e
            return DataDetailResponse(request, dataModel, f, key=emp.pk)
        for field in obj._meta.many_to_many:
            setattr(obj, field.name+"_set", tuple(getattr(obj, field.name).all()))

        if hasattr(dataModel.Admin, "form_after_save"):
            dataModel.Admin.form_after_save(request, obj_old, obj)
        post_check.send(sender=request, oldObj=obj_old, newObj=obj)
        return HttpResponse('{ Info:"OK" }')
    else:
        for i,v in dict(f.errors).items(): 
            print i, ":"
            for vi in v: print "\t", vi
        return DataDetailResponse(request, dataModel, f, key=emp.pk)

@login_required
def DataDetail(request, app_label, model_name, DataKey):
    from admin_detail_view import retUserForm,adminForm,doPostAdmin,doCreateAdmin
    dataModel=GetModel(app_label, model_name)
    if not dataModel: return NoFound404Response(request)
    lock=request.GET.get("_lock",None)
    read_only=(lock=='ALL')
    if not read_only:
            try: 
                    if dataModel.Admin.read_only: read_only=True
            except: pass
    perm=hasPerm(request.user, dataModel, "change")
    if not perm and not read_only: 
            if not hasPerm(request.user, dataModel, "browse"):
                    return NoPermissionResponse()
            read_only=True
    master=get_model_master(dataModel)        
    if dataModel==User:        # 管理员 管理
            if request.method=="POST" and not read_only:
                    if not perm: return NoPermissionResponse()
                    return doPostAdmin(request, dataModel, DataKey)
            else:
                    return doCreateAdmin(request, dataModel, DataKey)
    
    if master:
            try:
                    m_instance=master.rel.to.objects.get(pk=DataKey)
            except ObjectDoesNotExist:
                    return NoFound404Response(request)
            try:
                    instance=dataModel.objects.get(**{master.name:m_instance})
            except ObjectDoesNotExist:
                    instance=dataModel(**{master.name: m_instance})
    else:
            try:
                    instance=dataModel.objects.get(pk=DataKey)
            except ObjectDoesNotExist:
                    return NoFound404Response(request)
    level_type = get_leveltype_byhttpreferer(request)
    if request.method=="POST" and not read_only:
            if not perm: return NoPermissionResponse()
            return DataChangePost(request, dataModel, form_for_instance(instance, post=request.POST,level_type=level_type), instance)
    if lock:
            fields=[field.find("__") and field.split("__")[0] or field for field in dict(request.GET)]
    return DataDetailResponse(request, dataModel, 
            form_for_instance(instance, lock_fields=master and [master.name] or (lock and fields or []), read_only=read_only,level_type=level_type),instance.pk, instance)
#        return DataChangeGet(request, dataModel, form_for_instance(instance, lock_fields=master and [master.name] or []), instance)

#新增权限组时，如果是门禁权限组，则可编辑设备为非电梯控制器，如果是梯控权限组，则可编辑设备为电梯控制器
#根据HTTP_REFERER信息判断app，继而判定权限组类型
def get_leveltype_byhttpreferer(request):
    key_httpref = "HTTP_REFERER"
    level_type = 0
    if key_httpref in request.META.keys():
        iaccess_or_elevator = request.META.get("HTTP_REFERER")
        iaccess_or_elevator = iaccess_or_elevator.split("/")
        strcomp_app = "iaccess"
        strcomp_app_elevator ="elevator"
        strcomp_model = "AccLevelSet"
        strcomp_model_elevator ="ElevatorLevelSet"

        if strcomp_model in iaccess_or_elevator and strcomp_app in iaccess_or_elevator:
            level_type = 1#电梯权限组
        else :
            if strcomp_model_elevator in iaccess_or_elevator and  strcomp_app_elevator in iaccess_or_elevator:
                level_type = 2#梯控权限组
            else:
                level_type = 0
        return  level_type


