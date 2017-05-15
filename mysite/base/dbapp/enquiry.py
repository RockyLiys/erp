#coding utf-8
from django.db import connection,transaction,models
from django.db.models.fields.related import ForeignRelatedObjectsDescriptor as frod,ReverseSingleRelatedObjectDescriptor as rsrod
from django.http import HttpResponse
from django.db.models import Q

import types

charfield=[models.CharField,
            models.TextField,
            models.EmailField,
            models.FileField,
            models.ImageField,
            models.IPAddressField,
            models.URLField,
#            models.XMLField,
    ]
intfield=[
            models.AutoField,
            models.IntegerField,
            models.SmallIntegerField,
            models.FloatField,
            models.ForeignKey,
            models.OneToOneField,
            models.ManyToManyField,
            models.BooleanField,
            models.DecimalField,
            
]
datetimefield=[
    models.DateTimeField,
    models.DateField,
    models.TimeField,
]
def get_dbtype(fld):
    if type(fld) in charfield:
        return "nvarchar"
    elif type(fld) in intfield:
        return "int"
    elif type(fld) in datetimefield:
        return "datetime"
    else:
        return "nvarchar"

class Enquiry:
    def __init__(self,tablename):
        self.relatetable={}
        self.allfields=[]
        self.alltables=[]
        self.retvalue=[]
        self.allfieldsProperty={}
        self.tablename=tablename
        self.parentProperty={}
        self.subTableProperty={}
       
    def Search(self,tablename,**where):
        """
            para *tablename
                table name  only one in this ver. 
            para: **where
            desc: a  dict,each unit like 
                property__function:value
                
                relatetable:
                
                objectproperty__relateObjectProtperty__ParentRelateObjectProperty__.......__function:value
            
        """
        
        tb=self.findAllRelationTables(tablename)

        self.retvalue=tb[0].objects.filter(Q(**where))

        return self.retvalue
        
    def splitTablesAndFields(self,*Fields):    
        tablename=[]
        fields=[]
        for i in Fields:
            if "." in i:
                tmp=i.split(".")
                if tmp[0] not in tablename:
                    tablename.append(tmp[0])
                fields.append(i)
            else:
                tablename.append(i)
        return (tablename,fields)
        
    def getAllFields(self,*ObjectsList):

        self.allfields=[]
        
        
        for fld in ObjectsList: 
            searchable_fields=[]
            if hasattr(fld,'Admin'):
                if hasattr(fld.Admin,"adv_fields"):
                    tfields=fld.Admin.adv_fields
                else:   
                    if hasattr(fld.Admin,"list_display"):
                        tfields=fld.Admin.list_display                 
                    else:
                        tfields=[]
                if tfields:                    
                    for f in tfields:
                        if f.find(".")>0 or f.find("__")>0:
                            if f.find(".")>0:
                                f=f.split(".")
                            else:
                                f=f.split("__")                            
                            if f[0] not in searchable_fields:
                                searchable_fields.append(f[0])
                        elif f.find("|")>0:
                                pass
                        else:
                            searchable_fields.append(f)
                            
                        
            
            cname=fld.__name__   
            for fd in fld._meta.fields:
               if fd.name in searchable_fields or len(searchable_fields)==0:                        
                    fdname= cname+"." +fd.name 
                    if str(fdname).endswith("_id"):
                        fdname=fdname[:len(fdname)-3]          

                    self.allfields.append(fdname)
                    dbtype=get_dbtype(fd)
                    max_length=fd.max_length
                    help_text=u"%s"%fd.help_text
                    null=fd.null and fd.blank
                    att=[str(dbtype),str(max_length),help_text,u"%s"%fd.verbose_name,null]                 
                    
                    self.allfieldsProperty[fdname]=att

        #    self.allfields.sort()

        return self.allfieldsProperty
    
    def findAllRelationTables(self,tablename=None):
       
        if tablename:
            pass
        else:
            tablename=self.tablename               
        
        self.alltables=[]
        
        for tb in models.get_models():
                #print "%s:%s   %s    type tb: %s  tablename: %s "%(tb.__name__.lower(),tablename,   tb.__name__.lower() == tablename.lower(),type(tb.__name__.lower()),type(tablename.lower())) 
                if tb.__name__.lower() == tablename.lower():    
                    if tb not in self.alltables:
                        
                        self.alltables.append(tb)
                    self.findEachTable(tb,self.alltables,"","") 

        return self.alltables
    def findEachTable(self,model,tablename,parentProperty,parmodelname):
        if parmodelname=="":
            parmodelname+=model.__name__
        else:
            parmodelname+= "."+model.__name__
        for i in model.__dict__.keys():  
                             
            #if hasattr(tb.objects.model,i):
            objProperty=type(model.__getattribute__(model,i))
            #print objTable                       
            if objProperty is rsrod:
                
                xx=model.__getattribute__(model,i)
                if xx.field.rel.to not in tablename:
                    tablename.append(xx.field.rel.to)
                    
                self.relatetable[model.__name__+"."+i]= xx.field.rel.to.__name__
                pp=str(xx.field.name)                
                
                
                if xx.field.rel.to.__name__!=model.__name__:    
                    if pp.endswith("_id"):
                       pp=pp[:len(pp)-3]
                    pp+="__"
                    self.parentProperty[model.__name__+"."+xx.field.rel.to.__name__]=parentProperty+pp                    
                    self.subTableProperty[parmodelname+"."+i]=[parentProperty+pp,model.__name__+"."+xx.field.rel.to.__name__]
                    self.findEachTable(xx.field.rel.to,tablename,parentProperty+pp,parmodelname)
                #print "%s : %s" %(xx.field.rel.to.__name__,parentProperty)


