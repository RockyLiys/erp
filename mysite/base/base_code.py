#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db import models
from django.conf import settings
from mysite.base.cached_model import CachingModel
from mysite.base.translation import DataTranslation
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_str
from simplejson import dumps
# from mysite.base.dbapp.utils import getJSResponse

from django.conf import settings
visible_BaseCode=True
# if settings.APP_CONFIG.system.BaseCode=="False":
#     visible_BaseCode=False


class BaseCode(CachingModel):
    """
    数据代码表, 该代码表用于保存或限定一些常用数据代码，如“性别”、“职务”等
    数据代码仅仅是为了对数据进行代码化的管理，并规范使用。通常，数据代码是系统初始化的时候就要写入全部项目，该表在安装完成后就不需要对数据进行改动。对于需要维护、需要在运行中扩充、
    或者需要维护其他属性的数据项目，通常应独立为新的数据模型。
    """
    content = models.CharField(_(u'代码'), max_length=30)
    content_class = models.IntegerField(_(u'代码类别'), null=True, default=0, blank=True,editable=False)
    #parent = models.ForeignKey("BaseCode", verbose_name=_('parent code'), null=True, blank=True ,editable=False)
    display = models.CharField(_(u'显示'), max_length=30, null=True, blank=True)
    value = models.CharField(_(u'值'), max_length=30)
    remark = models.CharField(_(u'备注'), max_length=200, null=True, blank=True)
    is_add= models.CharField(_(u'是否是用户添加的'), max_length=4, null=True, blank=True,editable=False)#是否是用户添加进去的,默认为false
    def delete(self):
        if self.is_add!="true":
            raise Exception(_(u"系统初始化的记录不能删除！"))
        else:
            super(BaseCode,self).delete()
    def save(self, **args):
        tmp=BaseCode.objects.filter(content=self.content,display=self.display)
        if len(tmp)>0 and tmp[0].id!=self.id:#新增
            raise Exception(_(u'记录已经存在!'))
        elif len(tmp)==0:#新增
            self.is_add="true"
        super(BaseCode,self).save(**args)
    
        
    def __unicode__(self):
            return u"%s"%(self.display)
    def display_label(self):
            return DataTranslation.get_field_display(BaseCode, "display", self.display)
    class Meta:
            verbose_name=_(u"基础代码表")
    class Admin(CachingModel.Admin):
        menu_index=300
        visible=False
        list_display=( "display","value", "remark")
#        def initial_data(self):
#            #print "添加系统语言到代码表中"
#            for l in settings.LANGUAGES:
#                data={'content':'base.language', 'value':l[0], 'display':l[1]}
#                try:
#                    d=BaseCode.objects.get(**data)
#                except:
#                    BaseCode(**data).save()
                    
            

def base_code_by(content, content_class=None):
    #chinese_no_choice=["CN_NATION","IDENTITY","CN_PROVINCE"]#非中文这些字段默认为空
    try:
        from django.utils import translation
        qs=BaseCode.objects.filter(content=content)
        if content_class!=None:
            qs=qs.filter(content_class=content_class)
        qs=[(item[0], item[1])
            for item in qs.values_list('value','display')]
        #lan=settings.LANGUAGE_CODE
        #if lan!="zh-cn" and content in chinese_no_choice:
            #return ()
        return tuple(qs)
    except: 
            #import traceback; traceback.print_exc()
        return ()



def get_category(request):

    #qs = BaseCode.objects.filter(parent__isnull=True).values_list("id", "content")
    qs = BaseCode.objects.distinct().values_list("content")
    data=[]
    for o in qs:
        l=list(o) 
        l.append(_(u"%(name)s")%{'name':_(o[0])})
        data.append(l)
    return getJSResponse(smart_str(dumps(data)))
