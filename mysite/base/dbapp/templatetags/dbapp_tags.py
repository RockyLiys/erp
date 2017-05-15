#coding=utf-8
import datetime
from django import template
from django.conf import settings
from cgi import escape
from django.utils.translation import ugettext_lazy as _, ugettext
from django.core.cache import cache
from dbapp.datautils import hasPerm
from django.db import models
from django.utils.encoding import force_unicode, smart_str
from dbapp.additionfile import get_model_image
from ooredis import *
register = template.Library()
@register.inclusion_tag('dbapp_filters.html')
def filters(cl):
    return {'cl': cl}

def filter(cl, spec):
    return {'title': spec.title(), 'choices' : list(spec.choices(cl)), 'field': spec.fieldName()}
filter = register.inclusion_tag('dbapp_filter.html')(filter)


@register.filter
def filter_config_option(key):
    u"返回键所对应的值"
    from mysite.utils import get_option
    return  get_option(key)

@register.filter
def filter_emp_card(key):
    u"返回键所对应的值"
    try:
        card_no = key.field.initial
        from mysite.personnel.models.model_issuecard import IssueCard,CARD_VALID,CARD_STOP
        if not card_no:
            return True
        else:
            try:
                obj_card = IssueCard.objects.get(cardno=card_no,sys_card_no__isnull=False)#发了IC消费卡，隐藏编辑卡号功能
                return False
            except:
                return True
    except:
        import traceback;traceback.print_exc()
    


@register.simple_tag
def get_config_option(key):
    u"返回键所对应的值"
    from mysite.utils import get_option
    return  get_option(key)

@register.simple_tag
def get_cardserial_from_txt():
    from django.core.cache import cache
    from mysite.pos.pos_constant import TIMEOUT
    cache_count = cache.get("IC_Card_Count")
    number = 0
    if cache_count:
        number = int(cache_count)+1
        cache.set("IC_Card_Count",number,TIMEOUT)
    else:
        from mysite.personnel.models.model_issuecard import IssueCard
        from django.db import connection
        sql = "SELECT  max(sys_card_no) FROM personnel_issuecard"
        cursor = connection.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
#        count = IssueCard.all_objects.all().filter(sys_card_no__isnull=False).count()
        if row[0]:
            number = int(row[0])+1
        else:
            number +=1
        cache.set("IC_Card_Count",number,TIMEOUT)
    return number

@register.simple_tag
#"""
#cache.set("ZKECO_DEVICE_LIMIT",self.zkeco_limit,CACHE_TIMEOUT)
#cache.set("ATT_DEVICE_LIMIT",self.att_limit,CACHE_TIMEOUT)
#cache.set("MAX_ACPANEL_COUNT",self.acc_limit ,CACHE_TIMEOUT)
#cache.set("POS_DEVICE_LIMIT",self.pos_limit ,CACHE_TIMEOUT)
#cache.set("MEETING_DEVICE_LIMIT",self.meeting_limit ,CACHE_TIMEOUT)
#cache.set("EMPLOYEE_LIMIT",self.employee_count  ,CACHE_TIMEOUT)
#cache.set("DEPARTMENTS_LIMIT",self.dept_count  ,CACHE_TIMEOUT)
#cache.set("LOGIN_USER_LIMIT",self.login_user_count  ,CACHE_TIMEOUT)
#cache.set("TRIAL_DATE",self.trial_date  ,CACHE_TIMEOUT)
#cache.set("AUTHORIZE_DATE",self.auth_date  ,CACHE_TIMEOUT)
#cache.set("SERVICE_END_DATE",self.service_end_date  ,CACHE_TIMEOUT)
#cache.set("RETENTION_DATE",self.retention_date  ,CACHE_TIMEOUT)
#
#"""
def get_dog_info():
    u"返回加密狗信息"
    from mysite.authorize_fun import get_cache
    from mysite.utils import get_option 
    try:
        zkeco_count = get_cache("ZKECO_DEVICE_LIMIT") or 0
        zktime_count = get_cache("ATT_DEVICE_LIMIT") or 0
        zkaccess_count = get_cache("MAX_ACPANEL_COUNT") or 0
        zkpos_count = get_cache("POS_DEVICE_LIMIT") or 0
        MEETING_DEVICE_LIMIT = get_cache("MEETING_DEVICE_LIMIT")
        EMPLOYEE_LIMIT = cache.get("EMPLOYEE_LIMIT") or 0#人员数
        DEPARTMENTS_LIMIT = cache.get("DEPARTMENTS_LIMIT") or 0#部门数
        LOGIN_USER_LIMIT = cache.get("LOGIN_USER_LIMIT") or 0#登陆用户数
        TRIAL_DATE = cache.get("TRIAL_DATE") or None#试用时间
        AUTHORIZE_DATE = cache.get("AUTHORIZE_DATE") or None#登记授权日期
        SERVICE_END_DATE = cache.get("SERVICE_END_DATE") or None#免费服务时间
        RETENTION_DATE = cache.get("RETENTION_DATE")#备用参数
        
#        print "MEETING_DEVICE_LIMIT=%s,EMPLOYEE_LIMIT=%s,DEPARTMENTS_LIMIT=%s,LOGIN_USER_LIMIT=%s,TRIAL_DATE=%s,AUTHORIZE_DATE=%s,SERVICE_END_DATE=%s,RETENTION_DATE=%s"%(MEETING_DEVICE_LIMIT,EMPLOYEE_LIMIT,DEPARTMENTS_LIMIT,LOGIN_USER_LIMIT,TRIAL_DATE,AUTHORIZE_DATE,SERVICE_END_DATE,RETENTION_DATE)
        attinfo = ""
        accinfo = ""
        posinfo = ""
        empinfo = ""
        deptinfo = ""
        log_user_info = ""
        try_date_info = ""
        authorize_info = ""
        service_end_date_info = ""
        
        count = 0
        
        if zkeco_count!=0:
            info = u"总点数:%s"%zkeco_count
            count = zkeco_count
        else:
            if get_option("ATT"):
                count = zktime_count
                attinfo = u"考勤点数:%s "%count
            if get_option("IACCESS"):
                count += zkaccess_count
                accinfo = u"门禁点数:%s "%zkaccess_count
            if get_option("POS"):
                count += zkpos_count
                posinfo = u"消费点数:%s "%zkpos_count
            
#        if EMPLOYEE_LIMIT>0:
#            empinfo = u"</br>人员数:%s "%EMPLOYEE_LIMIT
#        if DEPARTMENTS_LIMIT>0:
#            deptinfo = u"部门数:%s "%DEPARTMENTS_LIMIT
#        if LOGIN_USER_LIMIT>0:
#            log_user_info = u"登陆用户数:%s "%LOGIN_USER_LIMIT
        if TRIAL_DATE:
            TRIAL_DATE = TRIAL_DATE[0:4] + "-" + TRIAL_DATE[4:6] + "-" + TRIAL_DATE[6:8]
            try_date_info = u"</br>试用截止时间:%s "%TRIAL_DATE
        if AUTHORIZE_DATE:
            AUTHORIZE_DATE = AUTHORIZE_DATE[0:4] + "-" + AUTHORIZE_DATE[4:6] + "-" + AUTHORIZE_DATE[6:8]
            authorize_info = u"授权登记时间:%s "%AUTHORIZE_DATE

        if SERVICE_END_DATE:
            SERVICE_END_DATE = SERVICE_END_DATE[0:4] + "-" + SERVICE_END_DATE[4:6] + "-" + SERVICE_END_DATE[6:8]
            service_end_date_info = u"</br>维护截止时间:%s "%SERVICE_END_DATE
        customer_info = u"</br>客户编码: %s"%settings.CUSTOMER_CODE
        info = u"总点数:%s "%count + attinfo + accinfo + posinfo + empinfo + deptinfo + log_user_info + service_end_date_info +  authorize_info + try_date_info + customer_info
        
        return info
    except:
        import traceback;traceback.print_exc()
        return ""


@register.simple_tag
def get_service_end_date():
    u"返回加密狗中免费维护截止时间"
    SERVICE_END_DATE = cache.get("SERVICE_END_DATE") or None#免费服务时间
    if SERVICE_END_DATE:
        SERVICE_END_DATE = SERVICE_END_DATE[0:4] + "-" + SERVICE_END_DATE[4:6] + "-" + SERVICE_END_DATE[6:8]
    return SERVICE_END_DATE

@register.simple_tag
def get_main_fan_area(key):
    u"返回IC消费系统参数中的主扇区代码"
    redis_obj_param = Dict("pos_obj_param")
    return  redis_obj_param['main_fan_area']

@register.simple_tag
def get_minor_fan_area(key):
    u"返回IC消费系统参数中的次扇区代码"
    redis_obj_param = Dict("pos_obj_param")
    return  redis_obj_param['minor_fan_area']

@register.simple_tag
def get_system_pwd(key):
    u"返回IC消费系统参数中的系统密码"
    from base.crypt import encryption,decryption
    redis_obj_param = Dict("pos_obj_param")
    return  decryption(redis_obj_param['system_pwd'])

@register.simple_tag
def get_max_money(key):
    u"返回IC消费系统参数中的卡最大值"
    redis_obj_param = Dict("pos_obj_param")
    return  redis_obj_param['max_money']


@register.simple_tag
def current_time(format_string):
    return str(datetime.datetime.now())

@register.simple_tag
def get_this_year():
	import datetime
	return datetime.datetime.now().strftime("%Y")


@register.filter
def escape_js_html(value):
    from django.utils.html import escape
    from django.template.defaultfilters import escapejs
    return escapejs(escape(value))

@register.filter
def format_date(fielddatetime):
    return fielddatetime.strftime("%Y-%m-%d")

@register.filter
def translate_str(str):
    from django.utils.translation import ugettext as _
    if str:
        return _(str)
    else:
        return ""

@register.filter
def format_int(float_value):
    try:
        return int(float_value)
    except:
        return -1

@register.filter
def format_shorttime(fielddatetime):
    try:    
        return fielddatetime.strftime("%H:%M")
    except:
        return None

@register.filter
def HasPerm(user, operation): #判断一个登录用户是否有某个权限
    return user.has_perm(operation)

@register.filter
def format_whether(value): 
    if value:
        return ugettext(u"是")
    else:
        return ugettext(u"否")

@register.filter
def format_whether2(value): 
    if value=="1":
        return ugettext(u"是")
    elif value=="2":
        return ugettext(u"否")
    else:
        return ugettext(u"处理中")

            
@register.filter
def reqHasPerm(request, operation): #判断一个当前请求的数据模型表是否有某个权限
    return hasPerm(request.user, request.model, operation)

@register.filter
def hasApp(app_label):
    from django.conf import settings
    if "&" in app_label:
        for app in app_label.split("&"):
            if app.strip() not in settings.INSTALLED_APPS: return False
        return True
    elif "|" in app_label:
        for app in app_label.split("|"):
            if app.strip() in settings.INSTALLED_APPS: return True
        return False
    return (app_label in settings.INSTALLED_APPS)

@register.filter
def get_device_types(site):
    from mysite.iclock.models.model_device import DEVICE_TYPE
    return dict(DEVICE_TYPE).keys()

#用于返回当前系统（站点)是否为oem
@register.filter
def is_oem(site):#site变量暂无实际意义。
    from django.conf import settings
    return settings.OEM 

#用于返回当前系统是否带会议
@register.filter
def has_meeting(site):#site变量暂无实际意义。
    from django.conf import settings
    if 'mysite.meeting' in settings.INSTALLED_APPS:
        return True
    return False 


##用于返回当前系统（站点)是否是带考勤的门禁管理系统
@register.filter
def is_zkaccess_att(site):#site变量暂无实际意义。
    from django.conf import settings
    return settings.ZKACCESS_ATT

#用5.0代码打4.5包，主要是功能差异。值为False代表当前为5.0软件。
@register.filter
def is_zkaccess_5to4(site):#site变量暂无实际意义。
    from django.conf import settings    
    return settings.ZKACCESS_5TO4

@register.filter
def is_single_elevator(site):#site变量暂无实际意义。
    from django.conf import settings    
    return settings.SINGLE_ELEVATOR


#当当前系统是门禁带简单考勤系统时，判断用户是否配置考勤模块
@register.filter
def is_contain_att(site):#site变量暂无实际意义。
    import dict4ini
    from django.conf import settings
    from redis_self.server import start_dict_server
    current_path = settings.APP_HOME
    if 'mysite.iaccess' in settings.INSTALLED_APPS:
        d_server = start_dict_server()
        is_contain_att = d_server.get_key('IS_CONTAINS_ATT')
        if is_contain_att == None:
            #print '*******read is_att from file***'
            app = dict4ini.DictIni(current_path+"/appconfig.ini")
            is_contain_att = app["iaccess"].has_key("is_contain_att") and app["iaccess"]["is_contain_att"] or "0"
            d_server.set_to_dict('IS_CONTAINS_ATT', is_contain_att)
        d_server.close()
        return settings.ZKACCESS_ATT and int(is_contain_att)
    return True

#用于判断当前系统支持的语言（settings中配置）
@register.filter
def has_language(lang):
    from django.conf import settings
    return lang in dict(settings.LANGUAGES).keys()


@register.filter
def buttonItem(request, operation): #根据一项操作产生操作菜单项!!!
    if hasPerm(request.user, request.model, operation):
        return u'<li><a href="%s/data/%s/">%s</a></li>'%(iclock_url_rel, model.__name__, model._meta.verbose_name)
    else:
        return u'<li>'+model._meta.verbose_name+'</li>'
    

@register.simple_tag
def version():
    return settings.VERSION+' by <a href="http://www.zksoftware.com">ZKSoftware Inc.</a>'

@register.simple_tag
def capTrans(s):
    return ugettext(u"%s"%s).capitalize()

@register.filter
def cap(s):
    return (u"%s"%s).capitalize()

@register.filter
def enabled_udisk_mod(mod_name):
    return ("udisk" in settings.ENABLED_MOD)
@register.filter
def enabled_weather_mod(mod_name):
    return ("weather" in settings.ENABLED_MOD)
@register.filter
def enabled_msg_mod(mod_name):
    return ("msg" in settings.ENABLED_MOD)
@register.filter
def enabled_att_mod(mod_name):
    return ("att" in settings.ENABLED_MOD)
@register.filter
def enabled_mod(mod_name):
    return (mod_name in settings.ENABLED_MOD)

@register.filter
def lescape(s):
    if not s: return ""
    s=escape(s)
    return escape(s).replace("\n","\\n").replace("\r","\\r").replace("'","&#39;").replace('"','&quot;')

@register.filter
def isoTime(value):
    if value:
        return str(value)[:19]
    if value==0:
        return "0"
    return ""

@register.filter
def stdTime(value):
    if value:
        return value.strftime(settings.STD_DATETIME_FORMAT)
    return ""


@register.filter
def shortTime(value):
    if value:
        return value.strftime(settings.SHORT_DATETIME_FMT)
    return ""

@register.filter
def vshortTime(value):
    if value:
        return value.strftime(settings.VSHORT_DATETIME_FMT)
    return ""

@register.filter
def shortDTime(value):
    if value:
        return value.strftime(settings.SHORT_DATETIME_FMT2)
    return ""

@register.filter
def onlyTime(value):
    if value:
        try:
            return value.strftime(settings.TIME_FMT)
        except:
            return (value+datetime.timedelta(100)).strftime(settings.TIME_FMT)
    else:
        return ""

@register.filter
def shortDate(value):
    if value:
        return value.strftime(settings.DATE_FMT)
    return ""

@register.filter
def shortDate4(value):
    if value:
        return value.strftime(settings.DATE_FMT4)
    return ""


@register.filter
def left(value, size):
    s=(u"%s"%value)
    if len(s)>size:
        return s[:size]+" ..."
    return s

@register.simple_tag#{% user_perms "personnel.Employee"%}
def user_perms(app_label_model_name):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    from dbapp.modelutils import GetModel
    from base.middleware import threadlocals
    user=threadlocals.get_current_user()
    split=app_label_model_name.split(".")
    m=GetModel(split[0],split[1])
    ct=ContentType.objects.get_for_model(m)
    perms=[p.codename for p in Permission.objects.filter(content_type=ct) if user.has_perm(split[0]+"."+p.codename)]
    perms=sorted(perms)
    return ".".join(perms)
    
@register.filter
def PackList(values, field):
    l=[]
    for s in values:
        l.append(s[field])
    return ','.join(l)

@register.filter
def detail_str(master_field):
    return u', '.join([u'%s'%obj for obj in master_field.all()])

#@register.filter
#def add_link(field):
    #from dbapp import urls
    #return u"<a class='link' href='1/?&_lock=1&device&door_no'>%s</a>"%(field)
    #return u"<a class='link' href='%s/?&_lock=1&device&door_no'>%s</a>"%(field)

@register.filter
def detail_list(master_field, split=u",", max_count=1000000):
    from dbapp import urls
    objs=master_field.all()
    filter, key=master_field.core_filters.items()[0]
    def edit_link(obj):
        return u"<a class='edit' href='%s?_lock=1&%s=%s'>%s</a>"%(\
            urls.get_obj_url(obj), filter, key, obj)
    def add_link():
        return u"<a class='new' href='%s?_lock=1&%s=%s'>%s</a>"%(\
            urls.get_model_new_url(master_field.model), filter, key, ugettext('Add'))
    has_add=max_count>len(objs)
    if not objs and has_add: return add_link()
    return split.join([edit_link(obj) for obj in objs])+(has_add and u" | "+add_link() or "")

@register.filter
#通用过滤器-----可供首卡开门、多卡开门使用
def detail_list_set(master_field, max_count=10000):
    from dbapp import urls
    model = master_field.__dict__['model']
    app_label = model._meta.app_label
    objs=master_field.all()
    filter, key=master_field.core_filters.items()[0]
    def add_link():
        return u"<a class='new' href='../../data/%s/%s/?_lock=1&%s=%s'>%s</a>"%(app_label, model.__name__, filter, key, ugettext(u'设置'))
    
    return ugettext(u'已设置数:%(d)d | %(s)s') % { 'd': objs.__len__(), 's': add_link()} or ""

@register.filter
def detail_list_emp(master_field, max_count=1000000):
    from dbapp import urls
    objs=master_field.all()
    filter, key=master_field.core_filters.items()[0]
    def edit_link(obj):
        return u"<a class='edit' href='%s?%s=%s?_lock=1'>%s</a>"%(\
            urls.get_obj_url(obj), filter, key, obj)
    def add_link():
        return u"<a class='new' href='%s?_lock=1&%s=%s'>%s</a>"%(\
            urls.get_model_new_url(master_field.model), filter, key, ugettext('Add'))
    has_add=max_count>len(objs)
    if not objs and has_add: return add_link()
    return u', '.join([edit_link(obj) for obj in objs])+(has_add and u" | "+add_link() or "")



@register.filter
#detail_list从表max_count为1的特殊情况
def detail_list_one(master_field, max_count=1):
    from dbapp import urls
    objs=master_field.all()#最多一条记录
    filter, key=master_field.core_filters.items()[0]
    def edit_del_link(obj):
        #m_objs = master_field.model.objects.all()
        return u"<a class='edit' edit='%s?_lock=1&%s=%s' href='javascript:void(0)'>%s</a> <a class='delete' delete='%s_op_/_delete/?K=%s' href='javascript:void(0)'>%s</a>"%(\
               urls.get_obj_url(obj), filter, key, ugettext(u'修改'), urls.get_model_data_url(master_field.model), urls.get_obj_url(obj).split("/")[-2], ugettext(u'删除'))
    def add_link():
        return u"<a class='new' new='%s?_lock=1&%s=%s' href='javascript:void(0)'>%s</a>"%(\
            urls.get_model_new_url(master_field.model), filter, key, ugettext(u'设置'))
    has_add=max_count>len(objs)
    if not objs and has_add: return add_link()
    return edit_del_link(objs[0])


def _(s): return s

CmdContentNames={'DATA USER PIN=':_(u'人员信息'),
    'DATA FP PIN=':_(u'指纹'),
    'DATA DEL_USER PIN=':_(u'删除人员'),
    'DATA DEL_FP PIN=':_(u'删除指纹'),
    'CHECK':_(u'检查服务器配置'),
    'INFO':_(u'更新服务器上的设备信息'),
    'CLEAR LOG':_(u'清除考勤记录'),
    'RESTART':_(u'重新启动设备'),
    'REBOOT':_(u'重新启动设备'),
    'LOG':_(u'检查并传送新数据'),
    'PutFile':_(u'发送文件到设备'),
    'GetFile':_(u'从设备传文件'),
    'Shell':_(u'执行内部命令'),
    'SET OPTION':_(u'修改配置'),
    'CLEAR DATA':_(u'清除设备上的所有数据'),
    'AC_UNLOCK':_(u'输出开门信号'),
    'AC_UNALARM':_(u'中断报警信号'),
    'ENROLL_FP':_(u'登记人员指纹'),
}

def getContStr(cmdData):
    for key in CmdContentNames:
        if key in cmdData:
            return CmdContentNames[key]
    return "" #_("Unknown command")

@register.filter
def cmdName(value):
    return getContStr(value)

DataContentNames={
    'TRANSACT':_(u'考勤记录'),
    'USERDATA':_(u'人员信息及其指纹')}

@register.filter
def dataShowStr(value):
    if value in DataContentNames:
        return value+" <span style='color:#ccc;'>"+DataContentNames[value]+"</span>"
    return value

@register.filter
def cmdShowStr(value):
    return left(value, 30)+" <span style='color:#ccc;'>"+getContStr(value)+"</span>"

@register.filter
def thumbnail_url(obj, field=""):
    try:
        url=obj.get_thumbnail_url()
        if url:
            try:
                fullUrl=obj.get_img_url()
            except: #only have thumbnail, no real picture
                return "<img src='%s' />"%url
            else:
                if not fullUrl:
                    return "<img src='%s' />"%url
            return "<a href='%s'><img src='%s' /></a>"%(fullUrl, url)
    except:
        import os
        f=getattr(obj, field or 'pk')
        if callable(f): f=f()
        fn="%s.jpg"%f
        fns=get_model_image(obj.__class__, fn, "photo", True) #image_file, image_url, thumbnail_file, thumbnail_url
        #print fns
        if fns[0]:
            if fns[2]: #has thumbnail
                return "<a href='%s'><img src='%s' /></a>"%(fns[1], fns[3])
            else:
                return "<a href='%s'><img src='%s' width='120'/></a>"%(fns[1], fns[1])
        elif fns[2]:
               return "<img src='%s' />"%fns[3]
    return ""

#表单里的label_suffix，非filter---add by darcy 20100605
def label_tag(field):
    label_suffix = ':'
    label_tag = field.label_tag()
    label = label_tag.split('<')[1].split('>')[1]
    if label[-1] not in ':?.!':
        label += label_suffix 
    return field.label_tag(label)

#表单里的label_suffix(无星号,可用于查询）---add by darcy 20100617
@register.filter 
def field_as_label_tag_no_asterisk(field):
    result = label_tag(field)
    if result.__contains__("required"):
        result = result.replace('required','')
    return """%s"""%result

@register.filter 
def foreignkey_no_load(field):
    return field.as_widget(attrs={'no_load':True})

#表单里的label_suffix(有星号（非必填项）,前端判空）---add by darcy 20101225
@register.filter 
def field_as_label_tag_asterisk(field):
    result = label_tag(field)
    if not result.__contains__("required"):
        result = result.replace('label for', 'label class="required" for')
    return """%s""" % result


#只返回label_tag包含：和for等
@register.filter 
def field_as_label_tag(field):
    return """%s""" % label_tag(field)

#返回help_text 字段中的注释
@register.filter 
def field_as_help_text(field):
    return field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""

@register.filter    
def field_format(field, fmt_str):
    return fmt_str%{ \
        'label_tag':label_tag(field), 
        'as_widget':field.as_widget(), 
        'errors':field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        'help_text':field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    }

@register.filter    
def field_as_td_h(field, colspan=1):
    #print "---------field=" ,field,"--type=",type(field)
    if field:
        #print "---------field=" ,field,"--type=",type(field)
        return """<th>%s</th><td%s>%s%s%s</td>"""%( \
            label_tag(field),
            colspan>1 and " colspan=%s"%colspan or "",
            field.as_widget(), 
            field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
            field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
        )
    else:
        return ""

#将表中无星号的在表单中添加星号（用户设备表等）
@register.filter    
def field_as_td_h_asterisk(field, colspan=1):
    return """<th>%s</th><td%s>%s%s%s</td>"""%( \
        field_as_label_tag_asterisk(field),
		colspan>1 and " colspan=%s"%colspan or "",
        field.as_widget(), 
        field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    )

    
@register.filter    
def field_as_ul_li(field):
    return """<div><ul><li>%s</li><li>%s%s%s</li></ul></div>"""%( \
        label_tag(field),  
        field.as_widget(), 
        #"<input type='text' name='%s'/>"%field.name,
        field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    )
    

@register.filter    
#用于不需要显示label的特殊模板
def field_as_td_h_special(field):
    return """<td>%s%s%s</td>"""%( \
        field.as_widget(), 
        field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    )

@register.filter    
#用于不需要显示label的特殊模板--不显示td
def field_as_no_td(field):
    return """%s%s%s"""%( \
        field.as_widget(), 
        field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    )

@register.filter    
#用于不需要显示label的特殊模板(带自动输入）
def field_as_td_h_tz(field):
    return """<td><div class='displayN'>%s%s%s</div><div id='%s'></div></td>"""%( \
        field.as_widget(), 
        field.errors and "<ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<span class='gray'>%s</span>"%unicode(field.help_text)) or "",
        field.name
    )


@register.filter    
def field_as_td_v(field):
    return """<td>%s<br/>%s%s%s</td>"""%( \
        label_tag(field), 
        field.as_widget(), 
        field.errors and "<br/><ul class='errorlist'>%s</ul>"%("".join(["<li>%s</li>"%e for e in field.errors])) or "",
        field.help_text and ("<br/><span class='gray'>%s</span>"%unicode(field.help_text)) or ""
    )


@register.filter
def int_color(color):
    if color:
        return "<span style='background-color: #%02x%02x%02x; padding-left: 1em;' class='color'>&nbsp;</span>"%(color>>16&0xff, color>>8&0xff ,color&0xff)
    else:
        return "<span class='color'>&nbsp;</span>"
@register.filter
def boolean_icon(value):
	if value:
		return u"<img src='%s/img/icon-yes.gif' alt='%s' />"%(settings.MEDIA_URL, ugettext(u'是'))
	return u"<img src='%s/img/icon-no.gif' alt='%s' />"%(settings.MEDIA_URL, ugettext(u'否'))

@register.filter
def treeview(dept, node="li"):
        TREE_SPACE="<%(n)s class='space'></%(n)s>"%{"n": node}
        TREE_PARENT_LINE="<%(n)s class='parent_line'></%(n)s>"%{"n": node}
        TREE_LEAF="<%(n)s class='leaf'></%(n)s>"%{"n": node}
        TREE_LAST_LEAF="<%(n)s class='last'></%(n)s>"%{"n": node}
        TREE_FOLDER="<%(n)s class='folder'></%(n)s>"%{"n": node}
        TREE_FIRST_FOLDER="<%(n)s class='folder first'></%(n)s>"%{"n": node}
        TREE_LAST_FOLDER="<%(n)s class='folder last'></%(n)s>"%{"n": node}
        TREE_CONVERT={'l':TREE_PARENT_LINE, ' ':TREE_SPACE, 'L':TREE_LAST_LEAF}
        TREE_FOLDER_CONVERT={'l':TREE_PARENT_LINE, ' ':TREE_SPACE, 'L':TREE_LAST_FOLDER}
        if not hasattr(dept, "tree_prefix") or not dept.tree_prefix:
                if dept.tree_folder:
                        ret=TREE_FIRST_FOLDER
                else:
                        ret=TREE_LEAF
        else:
                ret= [TREE_CONVERT[tp] for tp in dept.tree_prefix]
                if dept.tree_folder:
                        ret[-1]=TREE_FOLDER
                        if dept.tree_prefix[-1]=='L':
                                ret[-1]=TREE_LAST_FOLDER
                elif dept.tree_prefix[-1]=='L':
                        ret[-1]=TREE_LAST_LEAF
                else:
                        ret[-1]=TREE_LEAF
                ret=TREE_SPACE+(''.join(ret))
        return u"<span class='tree'>%s<span class='content'>%s</span></span>"%(ret, dept)

@register.filter
def mod_by(value, div):
	return int(value)%int(div)


#从后台获取视频联动的图片存储路径
@register.filter
def get_videolinkage_picture_savepath():
    from base.backup import get_attsite_file 
    db_dict = get_attsite_file()
    save_path = db_dict["Options"]["VIDEOLINKAGE_PICTURE_PATH"]
    #print"______-----save_path=",save_path,"---type=",type(save_path)
    return save_path
#是否为超级管理员
@register.filter
def is_superuser(user):
    if user.is_superuser:
        return True
    else:
        return False

