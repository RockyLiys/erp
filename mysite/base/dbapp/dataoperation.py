#coding=utf-8
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from modelutils import GetModel
from datautils import NoFound404Response
import types
from base.operation import Operation, ModelOperation
from django.shortcuts import render_to_response
from django.template import loader, RequestContext, Template, TemplateDoesNotExist
from widgets import form_field as form_field_default, form_field_readonly
from utils import getJSResponse
from django.http import HttpResponse
from django import forms
from django.db.models import Model
from django.db import models
from base.cached_model import CachingModel
from base.models_logentry import LogEntry
import datautils

def form_field(f, readonly=False, **kwargs):
    if readonly:
        return form_field_readonly(f, **kwargs)
    return form_field_default(f, **kwargs)

def get_form_(request,app_label, model_name, op_name):
#    from mysite import authorize_fun
#     #软件狗控制/*******start*******/
#    if not authorize_fun.can_operate(request):
#        if request.is_ajax():
#            return HttpResponse("session_fail_or_no_permission")
#        else:
#            return render_to_response('no_permission_info.html',RequestContext(request,{'dbapp_url': dbapp_url}))
    #/********end**********/
    is_worktable=""
    if request.META.has_key('HTTP_REFERER'):
        is_worktable=request.META['HTTP_REFERER']
    
    if is_worktable.find("worktable")!=-1:
        is_worktable=True
    else:
        is_worktable=False
    model=GetModel(app_label, model_name)
    if not model: return NoFound404Response(request)
    if not hasattr(model, op_name): return NoFound404Response(request)
    op=getattr(model, op_name)
    obj_op = None
    if not (type(op)==types.TypeType and issubclass(op, ModelOperation)):
            return NoFound404Response(request)
    if op_name.startswith("_"):
        opn= op_name[1:]
    else:
        opn=op_name
    if model.__name__=="Group":
        opn="groupdel"
        
#    if not datautils.hasPerm(request.user, model, opn.lower()):
#        return HttpResponse(_(u'会话已过期或没有权限'))
    if op_name=="View_detail":
        if request.method=="GET":
            data_key=request.REQUEST.get("K")
            return view_detail(request,app_label,model_name,data_key)
        else:
            return HttpResponse('{ Info:"OK" }')
    
    if request.method=='POST':
        if issubclass(model,Model) and not issubclass(model,CachingModel):
            keys=request.REQUEST.getlist("K")
            if not keys:
                #ModelOperation path
                try:
                    ret=model.model_do_action(op_name, request, form_field=form_field)
                    if not ret: return HttpResponse('{ Info:"OK" }')
                    if isinstance(ret, HttpResponse): return ret
                    if isinstance(ret, forms.Form):
                        f=ret
                        return HttpResponse(u"<div>%s</div>"%f.as_table())
                    else:
                        return HttpResponse(u"{ errorCode:-1,\nerrorInfo:\"%s\" }"%ret)
                except Exception, e:
                    return HttpResponse(u"{ errorCode:-1,\nerrorInfo:\"%s\" }"%e)
            else:
                ret=[]
                objs=model.objects.filter(pk__in=keys)
                try:
                    op_class=op
                    for obj in objs:
                        if len(op_class.params)==0:
                            op=op_class(obj)
                            ret.append("%s"%(op.action(**{}) or ""))
                            msg=u"%s(%s) %s"%(op.verbose_name, "", ret or "")
                            LogEntry.objects.log_action_other(request.user.pk,  obj , msg)
                except Exception, e:
                    ret.append(u"%s"%e)
                if not "".join(ret):
                    return HttpResponse('{ Info:"OK" }')
                else:
                    return HttpResponse('<ul class="errorlist"><li>%s </li></ul>'%("".join(ret)))
        else:
            try:
                ret=model.model_do_action(op_name, request, form_field=form_field)
                if not ret: return HttpResponse('{ Info:"OK" }')
                if isinstance(ret, HttpResponse): return ret
                if isinstance(ret, forms.Form):
                    f=ret
                    return HttpResponse(u"<div>%s</div>"%f.as_table())
                else:
                    return HttpResponse(u"{ errorCode:-1,\nerrorInfo:\"%s\" }"%ret)
            except Exception, e:
                return HttpResponse(u"{ errorCode:-1,\nerrorInfo:\"%s\" }"%e)
    elif request.method=="GET":
        if op.for_model:
            obj_op=op(model)
        else:
            key=request.GET.get('K',None)
            if key is None:
                obj_op =op(model())
            else:
                obj_op =op(model.objects.get(pk=key))
        f=obj_op.form(form_field, lock=request.GET.get('_lock', False), init_data=dict(request.GET))

    tmp_file=request.GET.get('_t',"%s_opform_%s.html"%(model.__name__,op.__name__))
    
    if hasattr(op, "help_text"):
        f.admin_help_text = op.help_text
    if hasattr(op, "verbose_name"):
        f.verbose_name = op.verbose_name
    
    if not issubclass(op, Operation):#ModelOperation(Operation是继承ModelOperation的)
        if hasattr(op, "tips_text"):#仅对ModelOperation
            f.tips_text = op.tips_text
    
    kargs={ 
            'form':f, 
            'op':op, 
            'obj_op':obj_op,
            'dataOpt':model._meta, 
            'title':(u"%s"%model._meta.verbose_name).capitalize(),
            'app_label':app_label,
            'model_name':model.__name__, 
            'is_worktable':is_worktable,
            'app':app_label,
            'detail': op_name,
    }
    kargs["app_menu"]=hasattr(model.Admin,"app_menu") and model.Admin.app_menu or  model._meta.app_label
    kargs["position"] = hasattr(model.Admin, "position") and model.Admin.position or None
    return render_to_response([tmp_file, 'data_opform.html'],
            RequestContext(request, kargs))        

def get_form(request,app_label, model_name, op_name):
    try:
            return get_form_(request, app_label, model_name, op_name)
    except:
            import traceback; traceback.print_exc()
            
        
def view_detail(request,app_label,model_name,data_key):
    u'''查看对象详情'''
    ModelClass=GetModel(app_label, model_name)
    op=getattr(ModelClass,"View_detail")
    try:
        instance = ModelClass.objects.get(pk=data_key)
        exclude_fields=['change_operator', 'change_time', 'create_operator', 'create_time', 'delete_operator', 'delete_time', 'status']
        #没有配置的时候需要排除CacheModel中的7个字段
        ret_fields={}
        view_fields=[]
        if hasattr(ModelClass.Admin,"view_fields"):
            view_fields=ModelClass.Admin.view_fields
        
        all_fields=ModelClass._meta.fields
        if view_fields:#配置了
            for e in view_fields:
                flag=False
                for ee in all_fields:
                    if ee.name==e:
                        value=instance.__getattribute__(ee.name)
                        if hasattr(instance,"get_"+e+"_display"):
                            value=(instance.__getattribute__("get_"+e+"_display")()) or ""
                        #if ee.editable:
                        ret_fields[u"%s"%ee.verbose_name]=value or ""
                        flag=True
                        break
                if not flag:
                    if hasattr(instance,e):
                        ret_fields[u"%s"%_(u"%s"%e)]= instance.__getattribute__(e)
        else:#没有配置
            for ee in all_fields:
                e_name=ee.name
                if e_name not in exclude_fields:
                    value=instance.__getattribute__(e_name) or ""
                    if hasattr(instance,"get_"+e_name+"_display"):
                        value=(instance.__getattribute__("get_"+e_name+"_display")()) or ""
                    #if ee.editable:
                    ret_fields[u"%s"%ee.verbose_name]=value
                        
        for m_m in ModelClass._meta.many_to_many:
            m_m_display=[]
            qs=instance.__getattribute__(m_m.name).get_query_set()
            for elem in qs:
                m_m_display.append(u"%s"%elem)
            ret_fields[m_m.verbose_name]=",".join(m_m_display)
        if hasattr(op, "verbose_name"):
            op_verbose_name=op.verbose_name
        else:
            op_verbose_name=u"%s"%_(u"详情")
        kargs={
            "fields":ret_fields,
            "app_menu":app_label,
            "title":(u"%s"%ModelClass._meta.verbose_name).capitalize(),
            "verbose_name":op_verbose_name
        }
        if hasattr(ModelClass,"render_view_obj") and callable(ModelClass.render_view_obj):
            #如果写了render_view_obj函数，则直接走此函数,该函数必须返回一个HttpResponse对象
            return ModelClass.render_view_obj(request)
        return render_to_response(["view_%s_detail.html"%model_name,"view_detail.html"],RequestContext(request, kargs))
    except Exception,e:
        return HttpResponse(u"%s"%e)

    
