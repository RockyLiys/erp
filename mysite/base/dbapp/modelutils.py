# -*- coding: utf-8 -*-

from django.db import models, connection
from django.db.models import Q
from django.template import Template,Context,loader,RequestContext,TemplateDoesNotExist
from django.utils import simplejson
from django.utils.encoding import smart_str
from base import cached_model
from django.db.models.fields.related import ForeignRelatedObjectsDescriptor as frod,ReverseSingleRelatedObjectDescriptor as rsrod
from enquiry import Enquiry
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render_to_response
from django.core.cache import cache
from base.middleware import threadlocals 
from django.utils.translation import  get_language

#from viewmodels import get_all_viewJson
import os
#视图入口
def setview(request,app_label,model_name):
    try:
        actions={}
        dataModel=""
        enq=Enquiry(model_name)
        x=enq.findAllRelationTables(None) 
        dataModel=x[0]
        x=[x[0]]
        fields=enq.getAllFields(*x)
        #视图类型
        from dbapp.models import VIEWTYPE_CHOICES
        viewtype=("%s"%n for n,v in VIEWTYPE_CHOICES)
        
        #操作权限
        if hasattr(dataModel,"get_all_operations"):
            action=dataModel.get_all_operations()
        else:
            action=[]
        for act in action:
            if hasattr(dataModel,act):
                pr=getattr(dataModel,act)
                actions[act]=u"%s"%pr.operation_name
        t=loader.get_template("view.html")
        
        relfield={}
        for name,value in enq.relatetable.items():
            relfield[value]=name
        #print relfield
       
       
        tfs={}
        #当前模型字段
        modelfields={}
        for fld in enq.allfields:
            if fld.split(".")[0]==dataModel.__name__:
                modelfields[fld.split(".")[1]]=fields[fld][3]
                tfs[fld]=fields[fld][3]
        
      
        #关联表字段
        for fld in enq.allfields:
            if fld.split(".")[0].lower()!=dataModel.__name__.lower():
                tfs[fld]=fields[relfield[fld.split(".")[0]]][3]+"." +fields[fld][3]

        #当前模型过滤器字段列表
        #print modelfields

        viewfilter={}
        try:
            if hasattr(dataModel.Admin,"list_filter"):
                for fld in dataModel.Admin.list_filter:
                    viewfilter[dataModel.__name__+"." +fld]=fields[dataModel.__name__+"."+fld][3]

        except:
            import traceback; traceback.print_exc()
            pass
        if viewfilter:
            has_filter=True
        else:
            has_filter=False
        if actions:
            hasaction=True
        else:
            hasaction=False
        
#        return t.render(RequestContext(request,{
#        'has_action':hasaction,'actions':actions,'fields':tfs,'modelfields':modelfields,
#                    'has_filter':has_filter,'viewfilter':viewfilter,
#                    'viewtype':viewtype,'all_fields':fields
#                    }))
#        
        return render_to_response("view.html",{
                            'has_action':hasaction,
                            'actions':actions,
                            'fields':tfs,
                            'modelfields':modelfields,
                            'has_filter':has_filter,
                            'viewfilter':viewfilter,
                            'viewtype':viewtype,
                            'all_fields':fields,
                    }
)
    except:
        
        import traceback; traceback.print_exc()
        
#高级查询入口
def advance_query_index(request,app_label,model_name):
    enq=Enquiry(model_name)
    x=enq.findAllRelationTables(None) 
    #print enq.parentProperty
    b=enq.getAllFields(*x)
    condition={
    "=":_(u"等于"),
    ">=":_(u"大于等于"),
    ">":_(u"大于"),
    "<=":_(u"小于等于"),
    "<":_(u"小于"),
    "in":_(u"满足任意一个"),
    "contains":_(u"含有"),
    "isnull":_(u"等于空值"),
  
    }
    #print condition
    html= writeDiv(enq.alltables,enq.allfields,enq.relatetable,enq.parentProperty,b,enq.subTableProperty)
    form=gen_form_fields(enq.alltables,enq.allfields)
    #print form.as_table()
    t=loader.get_template("advenquiry.html")
    #return t.render(RequestContext(request,{'tablesName':"enq_" +model_name,"div": html,"cond":condition}))
    return render_to_response("advenquiry.html",{'tablesName':"enq_" +model_name,"div": html,"cond":condition,'form':form})

def writeDiv(tables,fields,relfield,par,b,subtablepro):
    div=""
    #print subtablepro
    #print relfield
    #主表
    div +="""<div id='enq_"""+ tables[0].__name__+"""' class="mbmenu" > """
    flds=[x for x in fields if str(x).split(".")[0]==tables[0].__name__]
    for fl in flds:            
        t,f=fl.split(".")
        hasSubMenu=False
        subname=""
        children={}
        tmp=tables[0].__name__
        #查找是否有子菜单
        for n,v in subtablepro.items():
            if tmp==str(n[:n.rfind(".")]):
               children[str(n[n.rfind(".")+1:])] =v[0]
        if children.has_key(f):
            hasSubMenu=True
            subname=children[f]
        if hasSubMenu:
            div += """<a  class="{ menu:'enq_"""+ subname+ \
            """', img: '24-book-blue-check.png'}">%s</a>"""%b[fl][3]
        else:
            id=f
            div +=""" <a dbnull=' """+"%s"%b[fl][4]+""" '  dbtype=' """+"%s"%b[fl][0]+""" ' class="{action: 'onClick(\\' """ + id +""" \\' ,\\' """+ "%s"%b[fl][3] +""" \\', \\' """+ "%s"%b[fl][0] +""" \\',\\' """+ "%s"%b[fl][4] +""" \\')'}">%s</a> """%b[fl][3]
            div+="\n"
    div +="""</div>""" 
    div+="\n"
    #级联表
    for header,details in subtablepro.items():
        div +="""<div id='enq_"""+ details[0]+"""' class="mbmenu" > """
        flds=[x for x in fields if str(x).split(".")[0]==details[1].split(".")[1]]
        for fl in flds:            
            t,f=fl.split(".")
            hasSubMenu=False
            subname=""
            children={}
            tmp=str(header[:header.rfind(".")])+"."+details[1].split(".")[1]
            #查找是否有子菜单
            for n,v in subtablepro.items():
                if tmp==str(n[:n.rfind(".")]):
                   children[str(n[n.rfind(".")+1:])] =v[0]
            if children.has_key(f):
                hasSubMenu=True
                subname=children[f]
            if hasSubMenu:
                div += """<a  class="{ menu:'enq_"""+ subname+ \
                """', img: '24-book-blue-check.png'}">%s</a>"""%b[fl][3]
            else:
                id=details[0]+f
                div +=""" <a dbnull=' """+"%s"%b[fl][4]+""" ' dbtype=' """+"%s"%b[fl][0]+""" ' class="{action: 'onClick(\\' """ + id +""" \\' ,\\' """+ "%s"%b[fl][3] +""" \\' ,\\' """+ "%s"%b[fl][0] +""" \\',\\' """+ "%s"%b[fl][4] +""" \\')'}">%s</a> """%b[fl][3]
                div+="\n"
        div +="""</div>""" 
        div+="\n"
    
   # print "main *** sub div=", div
    return div
    
def gen_form_fields(tables,fields):
    from django.forms import forms,widgets as wg
    from django.forms import RadioSelect
    import widgets
    from django.db import models
    form=forms.Form()    
    for f in fields :   
        if f.split(".")[1] not in form.fields.keys():
            model=[t for t in tables if f.split(".")[0]==t.__name__][0]
            fd=model._meta.get_field(f.split(".")[1])
            if isinstance(fd,models.ForeignKey) or isinstance(fd,models.ManyToManyField):
                fd=fd.formfield(widget=wg.TextInput)
            else:
                try:
                    widget=None                               
                    #print "mf.class :%s"% mf.__class__
                    if hasattr(model,"Admin"):
                        if hasattr(model.Admin,"default_widgets"):
                            if model.Admin.default_widgets.has_key(f.split(".")[1]):
                                widget=model.Admin.default_widgets[f.split(".")[1]]
                    if not widget:
                        if fd.__class__ in widgets.WIDGET_FOR_DBFIELD_DEFAULTS:
                            widget=widgets.WIDGET_FOR_DBFIELD_DEFAULTS[fd.__class__]
                    
                    if widget==RadioSelect:                        
                        widget=None
                    if widget:
                        fd=fd.formfield(widget=widget)
                    else:
                        fd=fd.formfield()
                except:
                    import traceback;traceback.print_exc()
            form.fields[f.split(".")[1]]=fd
    
    
#    for f in fields:
#        if f.find('__')>0 or f.find('.')>0:
#            f=f.replace(".","__")
#            s,p=f.split("__")
#            pf=model._meta.get_field(s).rel.to._meta.get_field(p)     
#            if not pf.editable:
#                continue
#            fd=pf.formfield()            
#        else:           
#            mf=model._meta.get_field(f)
#            if not mf.editable:
#                continue
#            if isinstance(mf,models.ForeignKey) or isinstance(mf,models.ManyToManyField):                
#                fd=mf.formfield(widget=wg.TextInput)
#            else:
#                widget=None                               
#                #print "mf.class :%s"% mf.__class__
#                if mf.__class__ in widgets.WIDGET_FOR_DBFIELD_DEFAULTS:
#                    widget=widgets.WIDGET_FOR_DBFIELD_DEFAULTS[mf.__class__]
#                if widget:
#                    fd=mf.formfield(widget=widget)
#                else:
#                    fd=mf.formfield()
#        
#        #print form.as_table()
    return form
    

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

#取得当前用户创建整个模型界面框所需要的数据,包括权限，过滤器等等
#options全局缓存，actions按照用户缓存
def getUsrCreateFrameOptions(dataModel,request):
    from urls import get_model_data_url
    import base
    lng=get_language()
    
    model_name=dataModel.__name__
    
    #**********options cache********
    cache_key=u"%s_%s_%s"%(lng,model_name,'options')
    options=cache.get(cache_key)
    if not options:
        options={
                #"canEdit": (not hasattr(dataModel.Admin, 'read_only')) or not dataModel.Admin.read_only,
                "key_field":dataModel._meta.pk.name,
                "title":u"%s"%dataModel._meta.verbose_name,
                "addition_fields":[], 
                "addition_columns":[],
                "exception_fields":[],
                "model": model_name,
                #"model_url":get_model_data_url(dataModel),
                "app_label": dataModel._meta.app_label,
                "children_models": {},
                "detail_model":hasattr(dataModel.Admin, "detail_model") and [ m for m in dataModel.Admin.detail_model] or [],
                "parent_models":dict([(f.rel.to.__name__,f.name) for f in dataModel._meta.fields if isinstance(f,models.fields.related.ForeignKey)]),
                
        }
        
        if options["detail_model"]:
            all_related_objects = dataModel._meta.get_all_related_objects()
            for r in all_related_objects:
                child_fk_field = hasattr(r.model.Admin, 'child_fk_field') and r.model.Admin.child_fk_field or ''#只需要从表中存在多个对于主表的外键时配置。不配置取默认
                if child_fk_field and r.field.name != child_fk_field:#去掉不合要求的多余的对象（如video_linkageio__id）
                    all_related_objects.remove(r)
                
            options["children_models"] = dict([(r.name, [r.model._meta.app_label, r.model.__name__,\
                                                         u"%s"%r.model._meta.verbose_name, r.field.name\
                                                         ]) for r in all_related_objects\
                                              ])
        
        
        hide_fields=hasattr(dataModel.Admin, 'hide_fields') and list(dataModel.Admin.hide_fields) or[]
        if hide_fields:
            options["disable_cols"]=hide_fields
        
        if hasattr(dataModel.Admin,"sort_fields"):
            options["sort_fields"]=dataModel.Admin.sort_fields
            
        if hasattr(dataModel.Admin,"photo_path"):
            options["photo_path"]=dataModel.Admin.photo_path
        if hasattr(dataModel.Admin,"photo_path_tran"):
            options["photo_path_tran"]=dataModel.Admin.photo_path_tran
            
        if hasattr(dataModel.Admin,"layout_types"):
            options["layout_types"]=dataModel.Admin.layout_types
        if hasattr(dataModel.Admin,"scroll_table"):
            options["scroll_table"]=dataModel.Admin.scroll_table
        
        cache.set(cache_key,options,60*60*24*7)
        
        
    #*******actions cache*******
    ref_model = request.GET.get('ref_model',None)
    usr = threadlocals.get_current_user()
    cache_key = u"%s_%s_%s_%s_%s"%(lng,usr.username,model_name,ref_model,"actions")
    actions = cache.get(cache_key)
    if not actions:
        if hasattr(dataModel,"get_all_operation_js"):
                actions=dataModel.get_all_operation_js(request.user,ref_model)
        elif hasattr(dataModel.Admin, "read_only") and not dataModel.Admin.read_only:
                from dbapp.datautils import hasPerm
                actions={}
                if hasPerm(request.user,dataModel,"add"):
                    actions["_add"]={
                                "verbose_name":u"%(name)s"%{"name":_(u"新增")},
                                "help_text":u"%(name)s"%{"name":_(u"新增记录")},
                                "confirm":"",
                                "params":0,
                                "for_model":True,
                                "only_one":False,
                                }
                if ( hasPerm(request.user,dataModel,"delete") and model_name=="User" ) \
                    or ( hasPerm(request.user,dataModel,"groupdel") and model_name=="Group"):
                    actions["_delete"]={
                                "verbose_name":u"%(name)s"%{"name":_(u"删除")},
                                "help_text":u"%(name)s"%{"name":_(u"删除选定记录")},
                                "confirm":"are you sure?",
                                "params":0,
                                "for_model":False,
                                "only_one":False,
                                "for_select":True
                                }
                                
                if hasPerm(request.user,dataModel,"change"):
                    actions["_change"]={
                                "verbose_name":u"%(name)s"%{"name":_(u"修改")},
                                "help_text": u"%(name)s"%{"name":_(u"修改选定记录")},
                                "params":0,
                                "for_model":False,
                                "only_one":True,
                                "for_select":True
                                }
                actions =smart_str(simplejson.dumps(actions))
        cache.set(cache_key,actions,5*60)
    return (simplejson.dumps(options),actions or '{"op":"null"}')


DEFAULT_FILTER={
        models.DateTimeField: 'fmt_datetime',
        models.DateField: 'fmt_date',
        models.TimeField: 'fmt_time',
}

def default_filter(f):
        if f in DEFAULT_FILTER: return "|"+DEFAULT_FILTER[f]
        return ""

default_fields=[fld.name for fld in cached_model.CachingModel._meta.fields]

#获取构造模型数据列表所需要的数据
def getDefaultJsonDataTemplate(model, exception_fields=[], addition_fields=[], master_field=None):
        from datautils import change_to_master_field
        additionHeader={}
        if master_field:
                additionFields=[change_to_master_field(model, master_field, f) for f in addition_fields]
                exceptionFields=[change_to_master_field(model, master_field, f) for f in exception_fields]
        else:
                additionFields=addition_fields
                exceptionFields=exception_fields
        if additionFields:
                fs=[]
                for f in additionFields:
                        header=""
                        field=f
                        filter=""
                        if f.find("</th>")>=0:
                                header,field=f.split("</th>",1)
                                header+="</th>"
                                additionHeader[field]=header
                        fs.append(field)
                additionFields=fs

        if model.__class__==cached_model.MetaCaching:
                defDataList=["%s%s"%(f.name, default_filter(f.__class__)) for f in model._meta.fields if f.name not in default_fields]#('change_operator','create_operator','delete_operator','change_time','create_time','delete_time')]
        else:
                defDataList=["%s%s"%(f.name, default_filter(f.__class__)) for f in model._meta.fields]
        try:
                defDataListDefined=[f for f in model.Admin.list_display if f.find("_")!=0]
        except Exception, e:
                defDataListDefined=[]
        if defDataListDefined:
                defDataList=defDataListDefined

        if master_field:
                defDataList=[change_to_master_field(model, master_field, f) for f in defDataList]
    
        if additionFields:
                defDataList=defDataList+[f for f in additionFields if f not in defDataList]
        if exceptionFields:
                defDataList=[field for field in defDataList if (field not in exceptionFields)];
        if "pk" not in defDataList:
                if model._meta.pk.name not in defDataList:
                        defDataList.insert(0,model._meta.pk.name)
        defFieldList=defDataList
        defDataList=[]
        defHeaderList=[]
        for field in defFieldList:
                
                if ("get_"+field+"_display" in dir(model)):
                        defDataList.append('"{{ item.get_'+field+'_display }}"')
                elif not field:
                        defDataList.append('"{{ item }}"')
                elif field[0]=="|": #no field name, just a a filter for the object
                        defDataList.append('"{{ item|'+field.split("|")[1]+' }}"')
                else:
                        
                        if hasattr(model.Admin,"newadded_column"):
                                blnappend=False
                                for k,v in model.Admin.newadded_column.items():                                        
                                        if field==k:
                                                if hasattr(model.Admin,"master_field"):
                                                        defDataList.append('"{{ item.%s.%s}}"'%(master_field.related.var_name, v)) 
                                                        blnappend=True
                                                else:                                                        
                                                        defDataList.append('"{{ item.%s}}"'%v)
                                                        blnappend=True
                                                        break
                                if not blnappend:
                                        defDataList.append('"{{ item.%s }}"'%field)

                        else:
                                defDataList.append('"{{ item.%s }}"'%field)
                if field in additionHeader:
                        defHeaderList.append('"%s"'%additionHeader[field])
                elif "|" in field: #with a filter, which must be removed
                        f_name=field.split('|')
                        if f_name[0]: #has the field name
                                defHeaderList.append('"{{ cl.FieldName.%s }}"'%(f_name[0]))
                        else: #no field name
                                f_name=f_name[-1]
                                if ":" in f_name: f_name=f_name.split(":")[0]
                                defHeaderList.append(u'"%s"'%_(f_name)) #has head name or not
                else:
                        defHeaderList.append('"{{ cl.FieldName.%s }}"'%field.replace(".","__"))
        defHeaderList.append(u'"%s"'%_(u"描述"));
        defFieldList=['"%s"'%f for f in defFieldList]
        defFieldList.append('"data_verbose_column"');
        defDataList=[(f.find('|')>=0) and ('{%% autoescape off %%}%s{%% endautoescape %%}')%f or f for f in defDataList]
        defDataList.append('"{{ item }}"')
        #print 'before:%s\n',defDataList
        defDataList=[e.find("%}")==-1 and e[:-3].strip()+'|escapejs}}"' or (e[:e.find('}}"')].strip()+'|escapejs'+e[e.find('}}"'):]) for e in defDataList]#过滤特殊字符
        #print 'after:%s\n',defDataList
        temp=u"""{% autoescape off %}heads:["""+ u",".join(defHeaderList)+"""],        {% endautoescape %}
fields: ["""+ u",".join(defFieldList)+"""],
data:   [{% for item in latest_item_list %}
        ["""+(u",".join(defDataList))+u"""]{%if not forloop.last%},{%endif%}{% endfor %}
        ],
"""     
        return temp
        
def GetModel(app_label, model_name):
        dataModel=models.get_model(app_label,model_name)
        if not dataModel:
                dataModel=models.get_model("auth",model_name)
        if dataModel:
                if not hasattr(dataModel, "Admin"): dataModel.Admin=None
        return dataModel

def fieldVerboseName(model, fieldName):
        try:
                f = model._meta.get_field(fieldName)
                return f.verbose_name
        except:
                pass

def batchSql(sqls):
    for s in sqls:
        try:
            customSql(s)
            connection._commit()
        except:
            try:
                connection.close()
                customSql(s)
            except Exception, e:
                pass

