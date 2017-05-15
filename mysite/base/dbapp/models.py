# -*- coding: utf-8 -*-
from django.db import models, connection
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from base.operation import Operation,ModelOperation
import datetime
from utils import *
from django.conf import settings
from base.login_bio import BOOLEANS
from mysite.utils import get_option
VIEWTYPE_CHOICES = (
    ('personal', _(u'个人')),
    ('system', _(u'系统')),
)

#该应用是否可见
_visible=False

import views

import base


class init_db(base.models.AppOperation):
        verbose_name=_(u'初始化数据库')
        #view=views.init_db
        _app_menu="base"
        _menu_index=100000

#class Backup_db(base.models.AppOperation):
#        verbose_name=_(u'备份数据库')
#        view=views.backup_db
#        _app_menu="base"
#        operation_flag="false"
#        _menu_index=100000

class Restore_db(base.models.AppOperation):
        verbose_name=_(u'还原数据库')
        view=views.restore_db
        _app_menu="base"
        _menu_index=100000
        visible=False

class sys_option(base.models.AppOperation):
        verbose_name=_(u'系统参数设置')
        view=views.sys_option
        _menu_index=10001
        _app_menu="base"
        visible=False
        _menu_group = 'base'


class user_option(base.models.AppOperation):
        verbose_name=_(u'个性设置')
        visible=False
        view=views.user_option
        _app_menu="base"


SUCCESS_FLAG = (
    ('1', _(u'是')),
    ('2', _(u'否')),
    ('3', _(u'待处理')),
)
IM_FLAG = (
    (True,_(u'是')),
    (False,_(u'否')),
)
class DbBackupLog(base.models.CachingModel):
    user=models.ForeignKey(User, verbose_name=_(u"用户"))
    #备份时间
    starttime=models.DateTimeField(_(u'开始时间'), db_column='starttime', null=True, blank=True)
    #是否立即备份标志,主要针对手工备份
    imflag=models.BooleanField(_(u"立即备份"),choices=IM_FLAG)
    successflag=models.CharField(_(u"是否成功备份"), max_length=1,choices=SUCCESS_FLAG)  #是否成功备份

    def __unicode__(self):
        return self.user.username + "  " + self.starttime.strftime("%Y-%m-%d %H:%M:%S")

    def save(self):
        super(DbBackupLog,self).save()

    class Admin(base.models.CachingModel.Admin):
        disabled_perms=["add_dbbackuplog","change_dbbackuplog","dataimport_dbbackuplog"]
        menu_index=400
        app_menu="base"
        menu_group = 'base'
        visible=False
        list_display=('user.username','starttime','imflag|format_whether','successflag|format_whether2',)

    class Meta:
        db_table = 'dbbackuplog'
        verbose_name=_(u"数据库管理")

    class _change(Operation):
        help_text=_(u"修改选定记录")
        verbose_name=_(u"修改")
        visible=False
        confirm=""
        only_one_object=True
        def action(self):
                pass

    class OpBackupDB(ModelOperation):
        help_text=_(u"备份数据库，数据库服务器和本系统服务器必须在同一台电脑上，暂不支持备份Oracle数据库。如果备份失败，请参考用户手册中的用户使用FAQ。")
        verbose_name=_(u"备份数据库")
        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.mysql":
            visible = False
        def action(self):
            from base.models import PersonalOption,Option
            database_engine = settings.DATABASES["default"]["ENGINE"]
            if database_engine == "django.db.backends.oracle":#oracle
                raise Exception(_(u"暂不支持备份Oracle数据库"))
            backuptype=self.request.POST.get('backuptype','1')
            if backuptype=='1':
                try:
                    o=DbBackupLog(user=self.request.user,imflag=True,starttime=datetime.datetime.now())
                    o.save()
                except:
                    import traceback; traceback.print_exc()
            elif backuptype=='2':
                start = self.request.POST.get('start')
                inc = self.request.POST.get('intervaltime')
                #OptionClass["backup_sched"]= start +u"|" +inc
                cc=PersonalOption.objects.filter(user=self.request.user,option__name="backup_sched")
                id =Option.objects.filter(name__exact='backup_sched')[0]
                if cc:
                    cc[0].value=start +u"|" +inc
                    cc[0].save()
                else:
                    o=PersonalOption(user=self.request.user,value=start +u"|" +inc,option=id)
                    o.save()
            elif backuptype=="3":
                try:
                    cc=PersonalOption.objects.get(user=self.request.user,option__name="backup_sched")
                    cc.delete()
                except:
                    pass


#    class OpRestoreDB(ModelOperation):
#        help_text=_(u'还原数据库')
#        verbose_name=_(u"还原数据库")
#        def action(self):
#            pass
    class OpInitDB(ModelOperation):
        if get_option("POS"):
            help_text=_(u'''初始化数据库是将数据恢复到系统初始化状态!初始化人事信息,系统会清除历史消费记录,请慎用！''')
        else:
            help_text=_(u'''初始化数据库是将数据恢复到系统初始化状态!''')
        verbose_name=_(u"初始化数据库")
        def action(self):
            import time
            from dbapp.modelutils  import GetModel
            models_list=self.request.POST.getlist("KK")
            count=0
            for elem in models_list:
                count=count+1
#                print 'count: %s'%count
                split_models=elem.split("__")
                flag=True
                for i in split_models:
                    app_label,model_name=i.split(".")
                    model=GetModel(app_label,model_name)
                    if model:
                        if hasattr(model,"clear"):
                            try:
                                model.clear()
                                time.sleep(0.1)
                            except Exception,e:
                                flag=False
                                raise Exception(u"初始化:%(m)s,错误:%(e)s"%{
                                    "m":model._meta.verbose_name,
                                    "e":e
                                })
                        else:
                            for obj in model.objects.all():
                                try:
                                    #if(obj.Name=="弹性班次" and obj.Num_runID<=1):
                                     #   return
                                    #if(obj.Name=="员工排班")
                                    obj.delete()
                                    time.sleep(0.1)
                                except Exception,e:
                                    flag=False
                                    raise Exception(u"初始化:%(m)s,错误:%(e)s"%{
                                        "m":model._meta.verbose_name,
                                        "e":e
                                    })
    
                    else:
                        flag=False
#                if flag:
#                    print split_models,'ok\n'
#                else:
#                    print split_models,'fail\n'

class ViewModel(base.models.CachingModel):
        model=models.ForeignKey(ContentType)
        name=models.CharField(_(u'视图名称'),max_length=200)
        info=models.TextField(_(u'设置字符串,json使用对象的观点'))
        viewtype=models.CharField(_(u"视图类型"),max_length=20,choices=VIEWTYPE_CHOICES)
        class Admin(base.models.CachingModel.Admin):
                app_menu="base"
                visible=False
                cache=20*60*60*24
        def save(self):
                try:
                        super(ViewModel,self).save()
                except:
                        import traceback; traceback.print_exc()

                return self

class TimeField2(models.TimeField):
        pass
class ColorField(models.IntegerField):
        pass

def app_options():
    from base.options import  SYSPARAM,PERSONAL
    return (
        #参数名称, 参数默认值，参数显示名称，解释,参数类别,是否可见
        ('max_photo_width', '800', u"%s"%_(u'最大图片宽度'), '',PERSONAL,True ),
        ('theme', 'flat', u"%s"%_(u'风格'), "",PERSONAL,True),
        )



User.Admin.list_filter=('username',)


def create_model(name, base_model=base.models.CachingModel, attrs={}, meta_attrs={}, admin_attrs={}, module_path="dbapp.models"):
    attrs['__module__'] = module_path
    class Meta: pass
    Meta.__dict__.update(meta_attrs, __module__=module_path)
    attrs['Meta']=Meta
    if admin_attrs:
        if hasattr(base_model, "Admin"):
            class Admin(base_model.Admin): pass
        else:
            class Admin: pass
        Admin.__dict__.update(admin_attrs, __module__=module_path,app_label='dbapp')
        attrs['Admin']=Admin
    return type(name, (base_model,), attrs)

