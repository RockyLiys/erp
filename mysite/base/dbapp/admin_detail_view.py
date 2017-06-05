# coding=utf-8
from django.template import loader, Context, RequestContext, Library, Template, Context, TemplateDoesNotExist
from django.http import QueryDict, HttpResponse, HttpResponseRedirect, HttpResponseNotModified, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
import string, os
import datetime
import time
from django.db import models
from django.contrib.auth.decorators import login_required, permission_required
from django import forms
from django.utils.encoding import force_unicode, smart_str
from django.contrib.auth.models import User, Permission, Group
from django.utils.translation import ugettext as _
from django.utils.datastructures import SortedDict
from django.core.cache import cache
from utils import getJSResponse
from mysite.base.dbapp import widgets
from django.forms import CheckboxSelectMultiple
from mysite.base.dbapp import modelutils
import sys
from mysite.base.login_bio import OperatorTemplate
from django.contrib.auth.models import User
from mysite.base.models import options
from mysite import settings

class adminForm(forms.Form):
    def __init__(self, request, data=None, dataKey=None):
        model_dept = sys.modules['mysite.personnel.models.model_dept']
        Department = getattr(model_dept, 'Department')
        DeptManyToManyField = getattr(model_dept, 'DeptManyToManyField')
        model_deptadmin = sys.modules['mysite.personnel.models.model_deptadmin']
        model_areaadmin = sys.modules['mysite.personnel.models.model_areaadmin']
        DeptAdmin = getattr(model_deptadmin, 'DeptAdmin')
        AreaAdmin = getattr(model_areaadmin, 'AreaAdmin')
        model_area = sys.modules['mysite.personnel.models.model_area']
        Area = getattr(model_area, 'Area')
        AreaManyToManyField = getattr(model_area, 'AreaManyToManyField')
        depttree = sys.modules['mysite.personnel.models.depttree']

        ZDeptMultiChoiceDropDownWidget = getattr(depttree, 'ZDeptMultiChoiceDropDownWidget')(
            attrs={
                "async_model": "personnel__Department",
                "async_url": "/personnel/get_children_nodes/",
            }
        )
        ZAreaMultiChoiceDropDownWidget = getattr(depttree, 'ZDeptMultiChoiceDropDownWidget')(
            attrs={
                "async_model": "personnel__Area",
                "async_url": "/personnel/get_children_nodes/",
            }
        )

        self.request = request
        try:
            instance = User.objects.get(pk=dataKey)
            isAdd = False
        except:
            instance = None
            isAdd = True
        self.instance = instance
        opts = User._meta
        self.opts = opts
        exclude = ('user_permissions', 'password', 'is_active')
        if isAdd:
            exclude = exclude + ('last_login', 'date_joined')
        elif request.user.pk == instance.pk:
            exclude = exclude + ('is_staff', 'is_superuser', 'groups')
        field_list = []

        for f in opts.fields + opts.many_to_many:
            if not f.editable: continue
            if exclude and (f.name in exclude): continue
            if not isAdd:
                current_value = f.value_from_object(instance)
                formfield = f.formfield(initial=current_value)
            else:
                formfield = f.formfield()
            if formfield:
                field_list.append((f.name, formfield))
                if f.name in ('last_login', 'date_joined'):
                    formfield.widget.attrs['readonly'] = True

                if f.name in ('groups',):
                    try:
                        formfield.help_text = ""
                        formfield.widget = widgets.DivCheckboxSelectMultiple(choices=formfield.choices)
                    except:
                        import traceback;
                        traceback.print_exc()

        field_list.insert(1, ('is_resetPw', forms.BooleanField(label=_(u'重置密码'), initial=False, required=False)))
        formfield = forms.CharField(widget=forms.PasswordInput, label=_(u'密码'), initial=(isAdd and "" or "111111"))
        field_list.insert(2, ('Password', formfield))
        formfield = forms.CharField(widget=forms.PasswordInput, label=_(u'确认密码'), initial=(isAdd and "" or "111111"))
        field_list.insert(3, ('ResetPassword', formfield))

        fpid = OperatorTemplate.objects.filter(user=instance, fpversion="9")  # 查询当前用户有多少枚指纹及指纹ID号
        fpidcount = fpid.count()
        fpids = ''
        for i in range(fpidcount):
            if not fpids:
                fpids = str(fpid[i].finger_id)
            else:
                fpids = fpids + "," + str(fpid[i].finger_id)
        formfield = forms.CharField(label=_(u'用户指纹id'), widget=forms.TextInput, max_length=50, required=False,
                                    initial=fpids)
        field_list.insert(4, ('fpidnum', formfield))
        formfield = forms.CharField(label=_(u'用户指纹数'), widget=forms.TextInput, max_length=50, required=False,
                                    initial=fpidcount)
        field_list.insert(5, ('fpcount', formfield))


        lng = options['base.language']

        formfield = forms.CharField(label=_(u'语言'), widget=forms.TextInput, max_length=50, required=False, initial=lng)
        field_list.insert(6, ('tlng', formfield))

        self.depts = None
        self.deptadmins = None
        if not isAdd:
            try:
                self.deptadmins = DeptAdmin.objects.filter(user=instance)
                ids = self.deptadmins.values_list("dept")
                self.depts = Department.objects.filter(pk__in=ids)

            except:
                pass
        c = 4
        try:

            AuthedDept = DeptManyToManyField(Department, verbose_name=_(u'授权部门'))
            formfield = widgets.form_field(AuthedDept, initial=self.depts, required=False,
                                           widget=ZDeptMultiChoiceDropDownWidget, help_text=_(u"不选部门将默认拥有所有部门权限"))
            field_list.insert(c, ('AuthedDept', formfield))
        except:
            import traceback;
            traceback.print_exc()
        c = 4 + 1

        self.areas = None
        self.areaadmins = None
        if not isAdd:
            try:
                self.areaadmins = AreaAdmin.objects.filter(user=instance)
                ares_ids = self.areaadmins.values_list("area")
                self.areas = Area.objects.filter(pk__in=ares_ids)

            except:
                pass

        try:
            AuthedArea = AreaManyToManyField(Area, verbose_name=_(u'授权区域'))
            formfield = widgets.form_field(AuthedArea, initial=self.areas, required=False,
                                           widget=ZAreaMultiChoiceDropDownWidget, help_text=_(u"不选区域将默认拥有所有区域权限"))
            field_list.insert(c, ('AuthedArea', formfield))
        except:
            import traceback;
            traceback.print_exc()

        self.base_fields = SortedDict(field_list)
        forms.Form.__init__(self, data)

    def clean_username(self):
        import re
        username = self.cleaned_data.get('username', '')
        if not re.search(r'^[\w.@+-]+$', username):
            raise forms.ValidationError(_(u"用户名称必填。不多于30个字符。只能用字母数字或者@.+-_字符"))
        else:
            return username

    def clean_ResetPassword(self):
        p1 = self.cleaned_data.get('Password', '')
        p2 = self.cleaned_data.get('ResetPassword', '')
        if p1 == p2: return p2
        raise forms.ValidationError(_(u"密码必须一致"))

    def clean_Password(self):
        p1 = self.cleaned_data.get('Password', '')
        if len(p1) < 5 or len(p1) > 17:
            raise forms.ValidationError(_(u"密码长度必须大于4位,小于18位"))
        return p1

    def save(self):
        model_dept = sys.modules['mysite.personnel.models.model_dept']
        Department = getattr(model_dept, 'Department')
        DeptManyToManyField = getattr(model_dept, 'DeptManyToManyField')
        model_deptadmin = sys.modules['mysite.personnel.models.model_deptadmin']
        model_areaadmin = sys.modules['mysite.personnel.models.model_areaadmin']
        DeptAdmin = getattr(model_deptadmin, 'DeptAdmin')
        AreaAdmin = getattr(model_areaadmin, 'AreaAdmin')
        model_area = sys.modules['mysite.personnel.models.model_area']
        Area = getattr(model_area, 'Area')
        AreaManyToManyField = getattr(model_area, 'AreaManyToManyField')
        depttree = sys.modules['mysite.personnel.models.depttree']
        ZDeptMultiChoiceDropDownWidget = getattr(depttree, 'ZDeptMultiChoiceDropDownWidget')

        opts = self.opts
        u = self.instance
        try:
            if self.request.user.pk == self.instance.pk:
                u = self.request.user
        except:
            pass

        if u and self.cleaned_data['is_resetPw']:
            u.set_password(self.clean_Password())
        if not u:
            isexist = User.objects.all().filter(username=self.cleaned_data['username'])
            if isexist:
                pass
            else:
                u = User.objects.create_user(self.cleaned_data['username'],
                                             self.cleaned_data['email'], self.cleaned_data['Password'])

        for f in opts.fields + opts.many_to_many:
            if not f.editable: continue
            if f.name in self.cleaned_data:
                f.save_form_data(u, self.cleaned_data[f.name])

        try:
            if u.is_superuser:
                u.groups = []
                if self.deptadmins:
                    self.deptadmins.delete()
                if self.areaadmins:
                    self.areaadmins.delete()
                u.save()
                return u
            else:
                u.save()
        except:
            import traceback;
            traceback.print_exc()

        try:
            if self.deptadmins:
                self.deptadmins.delete()
            depts = self.cleaned_data['AuthedDept']
            checked_child = self.request.REQUEST.get("AuthedDeptchecked_child", None)
            if depts:
                depts = list(depts.values_list("pk", flat=True))
                if checked_child:
                    depts = get_dept_from_all(depts)

            # if not depts:return u
            for t in depts:
                d = Department.objects.get(id=t)
                DeptAdmin(user=u, dept=d).save()

            if self.areaadmins:
                self.areaadmins.delete()
            areas = self.cleaned_data['AuthedArea']
            checked_child = self.request.REQUEST.get("AuthedAreachecked_child", None)
            if areas:
                areas = list(areas.values_list("pk", flat=True))
                if checked_child:
                    areas = get_area_from_all(areas)

            for t in areas:
                d = Area.objects.get(id=t)
                AreaAdmin(user=u, area=d).save()
        except:
            import traceback;
            traceback.print_exc()
            # errorLog()
        return u


def retUserForm(request, f, isAdd=False):
    from urls import dbapp_url
    request.dbapp_url = dbapp_url
    d = []
    dd = []
    c = ""
    try:
        if f.depts:
            for t in f.depts:
                d.append(int(t.id))
                c += t.name + ','
        if f.areas:
            for t in f.areas:
                dd.append(int(t.id))
        cc = {"deptIDs": d, "deptTitle": c[:-1], "areaIDs": dd}
        dataModel = modelutils.GetModel('auth', 'User')
        inputFields, dtFields = ModifyFields(dataModel)
        inputFields = inputFields + ',AuthedDept' + ',Password' + ',ResetPassword,' + 'fgidnum'
    except:
        import traceback;
        traceback.print_exc()
    if hasattr(dataModel.Admin, "help_text"):
        f.admin_help_text = dataModel.Admin.help_text

    kargs = {"form": f, "dbapp_url": dbapp_url, "inputFields": inputFields, "dtFields": dtFields, "isAdd": isAdd,
             "add": isAdd, "dataOpt": User._meta, "model_name": User.__name__, "request": request,
             "title": (u"%s" % User._meta.verbose_name).capitalize(),
             "app_menu": hasattr(User.Admin, "app_menu") and User.Admin.app_menu or User._meta.app_label}
    return render_to_response([User.__name__ + '_edit.html', 'data_edit.html'], cc,
                              RequestContext(request, kargs, ), )


def doCreateAdmin(request, dataModel, dataKey=None):  # 生成 管理员 管理 页面
    if dataKey == "_new_":
        if request.user.has_perm('add_user'):
            f = adminForm(request, dataKey=dataKey)
            return retUserForm(request, f, isAdd=True)
    elif dataKey:
        f = adminForm(request, dataKey=dataKey)
        if not f.instance:
            return HttpResponseNotFound(_(u"关键字段%(object_name)s数据不存在!") % {'object_name': dataKey})
        return retUserForm(request, f)
    return render_to_response('info.html', RequestContext(request, {
        'content': _(u'没有权限'),
    }))


def doPostAdmin(request, dataModel, dataKey=None):  # 管理员 管理
    f = adminForm(request, data=request.POST, dataKey=dataKey)
    if not f.is_valid():
        return retUserForm(request, f, isAdd=(dataKey == "_new_"))
    else:
        try:
            old_user = {}
            if dataKey and dataKey != "_new_":
                u_old = User.objects.get(pk=dataKey)
                old_user = {
                    "username": u_old.username,
                    "first_name": u_old.first_name,
                    "last_name": u_old.last_name,
                    "email": u"%s" % u_old.email,
                    "is_staff": u_old.is_staff,
                    "is_superuser": u_old.is_superuser,
                    "last_login": u_old.last_login,
                    "groups": ",".join([str(e.pk) for e in u_old.groups.get_query_set()])
                }

            u = f.save()
            k = "user_id_%s" % u.pk
            cache.delete(k)

            new_user = {}
            if dataKey and dataKey != "_new_":
                new_user = {
                    "username": u.username,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "email": u"%s" % u.email,
                    "is_staff": u.is_staff,
                    "is_superuser": u.is_superuser,
                    "last_login": u.last_login,
                    "groups": ",".join([str(e.pk) for e in u.groups.get_query_set()])
                }
                change_info = []
                for k, v in old_user.items():
                    if new_user[k] != v:
                        change_info.append(u"%s(%s->%s)" % (k, v, new_user[k]))

                from base.models_logentry import LogEntry, CHANGE
                from django.contrib.contenttypes.models import ContentType
                LogEntry.objects.log_action(
                    user_id=request.user and request.user.pk or None,
                    content_type_id=ContentType.objects.get_for_model(User).pk,
                    object_id=u.pk,
                    object_repr=u.username,
                    action_flag=CHANGE,
                    change_message=";".join(change_info)
                )
        except:
            return render_to_response("info.html", {"title": _(u"用户"),
                                                    "content": u"<ul class='errorlist'><li>%(username)s %(store)s</li></ul>" % {
                                                        "username": f.cleaned_data['username'], "store": _(u"用户已经存在")}
                                                    })
        save_operatorfinger(request)  # 保存用户指纹
        del_operatorfinnger(request)  # 删除用户指纹
        return getJSResponse('{ Info:"OK" }')


def ModifyFields(dataModel):
    fields = dataModel._meta.fields
    dtFields = ''  # 日期时间 字段，加日历和时间
    inputFields = ''  # 必输字段
    for field in fields:
        if "DateTimeField" in str(type(field)):
            dtFields += field.name + ','
        if field.name != 'id':
            if (not field.blank) or field.primary_key:
                inputFields += field.name + ','
    if dtFields:
        dtFields = dtFields[:-1]
    if inputFields:
        inputFields = inputFields[:-1]
    return inputFields, dtFields


# 保存用户的指纹
def save_operatorfinger(request):
    operator = request.REQUEST.get("username", "")
    flag = request.REQUEST.get("actflag", "")
    if operator and flag == "register":
        fp_user = User.objects.filter(username=operator)
        if fp_user:
            fingger = request.REQUEST.get("finnger", "")
            fptemplate = request.REQUEST.get("template", "")
            if fingger and fptemplate:
                fingger = fingger.split(",")
                fptemplate = fptemplate.split(",")
                for i in range(len(fingger)):
                    t9 = OperatorTemplate.objects.filter(user=fp_user[0], finger_id__exact=fingger[i], fpversion="9")
                    try:
                        if not t9:
                            t9 = OperatorTemplate()
                        else:
                            t9 = t9[0]
                        t9.user = fp_user[0]
                        t9.template1 = fptemplate[i]
                        t9.finger_id = fingger[i]
                        t9.fpversion = "9"
                        t9.save()
                    except:
                        import traceback;
                        traceback.print_exc()
            fingger10 = request.REQUEST.get("finnger10", "")
            fptemplate10 = request.REQUEST.get("template10", "")
            # print         "fingger:%s"%fingger
            # print "        template:%s"%template
            if fingger10 and fptemplate10:
                fingger10 = fingger10.split(",")
                fptemplate10 = fptemplate10.split(",")
                for i in range(len(fingger10)):
                    t10 = OperatorTemplate.objects.filter(user=fp_user[0], finger_id__exact=fingger10[i],
                                                          fpversion="10")
                    if not t10:
                        t10 = OperatorTemplate()
                    else:
                        t10 = t10[0]
                    t10.user = fp_user[0]
                    t10.template1 = fptemplate10[i]
                    t10.finger_id = fingger10[i]
                    t10.fpversion = "10"
                    t10.save()


# 删除用户指纹
def del_operatorfinnger(request):
    operator = request.REQUEST.get("username", "")
    delfingger = request.REQUEST.get("delfp", "")
    flag = request.REQUEST.get("actflag", "")
    if delfingger and flag == "delete":
        fp_user = User.objects.filter(username=operator)
        delfingger = delfingger.split(",")
        for i in range(len(delfingger)):
            try:
                t = OperatorTemplate.objects.filter(user=fp_user[0], finger_id__exact=delfingger[i])
                # tcount = OperatorTemplate.objects.count()
                # print 'tcount=',tcount
                if t:
                    t.delete()
                    # print '*********** Delete the finger of user is successful! *************************'
            except:
                import traceback;
                traceback.print_exc()
        return HttpResponse('ok')
    else:
        # print '*********** Delete the finger of user is failed! ********************'
        return HttpResponse('')
