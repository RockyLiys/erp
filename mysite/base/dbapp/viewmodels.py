from models import ViewModel
from django.utils.translation import ugettext_lazy as _
from base.middleware import threadlocals
from django.http import HttpResponse
from modelutils import GetModel
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson   

from utils import getJSResponse
from django.utils.encoding import smart_str

def save_view(request, app_label, model_name):        
        try:
                ret={}
                op=threadlocals.get_current_user()
                #print op
                obj=GetModel(app_label, model_name)
                para=dict(request.POST)        
                view_name=para['viewname'][0]
                defaultview=""
                
                
                vi=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(obj),name__exact=view_name,create_operator__exact=op.username)
                if vi:
                        newview=vi[0]
                else:
                        newview=ViewModel()                
                newview.name=para['viewname'][0]
                newview.viewtype=para['viewtype'][0]
                col_set=[]
                fun_set={}
                filter_set={}
                other_set={}
                sort={}
                fieldswidth={}
                sort["firstsort"]=[para['firstsort'][0],para['sort1'][0]]
                sort["secondsort"]=[para['secondsort'][0],para['sort2'][0]]
                field_prefix="%s."%obj.__name__
                flen=len(field_prefix)
                #print field_prefix, flen
                view_property={}
                col=[]
                for name,value in para.items():
                        if name not in ['viewname','firstsort','secondsort','sort1','sort2','viewtype']:
                                if name.startswith("_fun_"):                                        
                                        
                                        fun_set[name[5:]]=value[0]                                        
                                        
                                elif name.startswith("_col_"):
                                        name=name[5:]
                                        
                                        if name.find(field_prefix)==0:
                                                col.append([value[0],str(name[flen:])])
                                        elif name.find('.')>0:
                                                col.append([value[0],"__".join(name.split('.'))])
                                
                                elif name.startswith("_filter_"):
                                                filter_set[name[8:]]=value[0]
                                        
                                elif name.startswith("_other_"):
                                        other_set[name[7:]]=value[0]
                                elif name.startswith("_txt_"):
                                        fieldswidth[name[5:]]=value[0]
                                else:
                                        view_property[name]=value[0]
                #print pset
                col.sort()
                for i in col:
                        col_set.append(i[1])
                defaultview=""
                if para.has_key('defaultview'):
                        defaultview='true'
                        view_property['defaultview']='true'
                if defaultview=='true':
                        #print 'find'
                        allvi=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(obj),create_operator__exact=op.username)
                        for v in allvi:
                                info=eval(v.info)
                                #print info
                                info["defaultview"]='false'
                                v.info=simplejson.dumps(info)
                                v.save()
                
                view_property['fields']=col_set
                view_property['action']=fun_set
                view_property['filter']=filter_set
                view_property['other']=other_set
                view_property['sort']=sort                
                
                view_property['fieldswidth']=fieldswidth                
                pset=simplejson.dumps(view_property)
                newview.info=pset
                newview.model=ContentType.objects.get_for_model(obj)
                newview.save()
                vj=get_all_viewJson(obj)
                
        except:
                import traceback; traceback.print_exc()
                
                ret["flag"]="false"
                ret["msg"]="save fail"
                ret["options"]=""
                return getJSResponse(smart_str(simplejson.dumps(ret)))
        ret["flag"]="true"
        ret["msg"]="save success!"
        ret["options"]=vj
        
        return getJSResponse(smart_str(simplejson.dumps(ret)))
def delete_view(request, app_label, model_name,view_name):
        try:
                        
                model=GetModel(app_label, model_name)
                op=threadlocals.get_current_user()
                
                ret=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(model),name__exact=view_name,create_operator__exact=op.username)
                if len(ret)<=0:
                        return HttpResponse("View not found or You are not the view's creator !")
                ret.delete()
        except:
                return HttpResponse("delete fail !")
        return HttpResponse("delete Ok !")
        
def get_view(request, app_label, model_name,view_name):
        model=GetModel(app_label, model_name)
        op=threadlocals.get_current_user()

        obj=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(model),name__exact=view_name,create_operator__exact=op.username)
        ret=""
        if len(obj)>0:                
                ret=eval(obj[0].info)
                ret["viewtype"]=obj[0].viewtype
                ret=simplejson.dumps(ret)
        return getJSResponse(ret)
        #return HttpResponse(ret)
def get_all_view(model):
        op=threadlocals.get_current_user()
        
        vn=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(model),create_operator__exact=op.username)        
        
        return [i.name for i in vn]
def get_all_viewJson(model):
        op=threadlocals.get_current_user()
        
        vn=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(model),create_operator__exact=op.username)        
        ret={}
        for i in vn:
                t=eval(i.info)
                t["viewtype"]=i.viewtype
                ret[i.name]=t
        
        return ret

def get_view_byname_js( model,view_name):        
        op=threadlocals.get_current_user()
        obj=ViewModel.objects.filter(model__exact=ContentType.objects.get_for_model(model),name__exact=view_name,create_operator__exact=op.username)
        ret=""
        if len(obj)>0:                
                ret=eval(obj[0].info)
                ret["viewtype"]=obj[0].viewtype
                ret={view_name:ret}
        return ret

