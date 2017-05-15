#coding=utf-8

from dbapp import dataviewdb
from dbapp import utils
from django.core.urlresolvers import reverse
from dbapp.models import create_model
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.query import QuerySet


def data_list(request, fn):
    attrs, admin_attrs, data=utils.load_tmp_file(fn)
    #print "attrs:%s"%attrs
    #print "admin_attrs:%s"%admin_attrs
    
    model=create_model(fn.encode("utf-8"), base_model=models.Model, attrs=attrs, admin_attrs=admin_attrs)
    return dataviewdb.model_data_list(request, model, QSList(model,data), model_url=reverse(data_list, args=(fn,)))
    
class QSValue(object):
    def __init__(self, index, data):
        self.data=data
        self.index=index
    def __getitem__(self, i):
        return self.data.get(i, self.index) or ""
    def __str__(self):
        return ""

class QSList(QuerySet):
    def __init__(self, model, data):
        self.model=model
        ret=[]
        start=0
        for item in data:
            start+=1
            ret.append(self.model(id=start,**item))
        self.data=ret
    def count(self):
        return len(self.data)
    def __len__(self):
        return len(self.data)
    def __iter__(self):
        return iter(self.data)
    def order_by(self, *fields):
        return self
    def __getitem__(self, i):
        return self.data[i]
        #return [QSValue(index, ret[index]) for index in range(len(ret))]
    
def save_datalist(data):
    fn="_tmp_%s"%id(data)
    head=data['heads']
    attrs=dict([(str(k), models.CharField(max_length=1024, verbose_name=head[k])) for k in data['fields']])
    admin_attrs={"read_only":True, "cache": False, "log":False}
    utils.save_tmp_file(fn, (attrs, admin_attrs,  data['data']))
    return fn
    
def response_datalist(request, data):
    fn="_tmp_%s"%id(data)
    attrs=dict([(k, models.CharField(max_length=1024, verbose_name=k)) for k in data['fields']])
    admin_attrs={"read_only":True, "cache": False, "log":False}
    utils.save_tmp_file(fn, (attrs, admin_attrs,  data['data']))
    model=create_model(fn, base_model=models.Model, attrs=attrs, admin_attrs=admin_attrs)  
    return dataviewdb.model_data_list(request, model, QSList(model,data['data']), model_url=reverse(data_list, args=(fn,)))

def data_demo(request):
#    from mysite.iclock.models import Device
#    data={}
#    data['data']=list(Device.objects.all()[:1000].values("sn", "alias", "last_activity", "log_stamp"))
#    data['fields']=["sn", "alias", "last_activity", "log_stamp"]
#   
#    return response_datalist(request, data)
    return ""

