# -*- coding: utf-8 -*-
from django import forms
# from django.forms.util import flatatt
# from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.safestring import mark_safe
from django.conf import settings
# from models import TimeField2, ColorField
from django.db import models
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template, loader, TemplateDoesNotExist
# from mysite.base.models import ZManyToManyField
import datetime

MEDIA_URL = settings.MEDIA_URL
CHOOSE_ALL = _(u'全部')
zbase_media = (
    #        MEDIA_URL+"/jslib/jquery.js",
    #        MEDIA_URL+"/jslib/jquery-ui-1.7.2.custom.js",
    #        MEDIA_URL+"/jslib/widgets.js",
)
zbase_css = (
    #        MEDIA_URL+"/css/jquery-ui-1.7.2.custom.css",
    #        MEDIA_URL+"/jslib/widgets.css",
)

DEFAULT_DT_FMT = "%Y-%m-%d %H:%M:%S"
from mysite.base.options import options


def str2datetime_(s, formats=(DEFAULT_DT_FMT,)):
    s = str(s)
    for fmt in formats:
        try:
            return datetime.datetime.strptime(s, fmt)
        except:
            pass
    d = None
    s = s.lower().strip()
    pm = False
    if s[-2:] == 'am': s = s[:-2]
    if s[-2:] == 'pm':
        pm = True
        s = s[:-2]
    if len(s.strip()) <= 5:
        s = s.strip() + ":00"
    for fmt in formats:
        try:
            d = datetime.datetime.strptime(s, fmt)
            break
        except:
            pass
    if d and pm:
        if d.hour < 12:
            d += datetime.timedelta(hours=12)
    return d


def str2date(s):
    return str2datetime_(s, ['%Y-%m-%d', str(options['base.date_format']), '%y-%m-%d'])


def str2datetime(s):
    return str2datetime_(s, [DEFAULT_DT_FMT, str(options['base.datetime_format']), str(options['base.date_format']),
                             str(options['base.shortdate_format'])])


def str2time(s):
    # return str2datetime_(s, [str(options['base.time_format'])])
    # 修改strptime转时间格式时，不需要日期
    # print str2datetime_(s, [str(options['base.time_format'])])
    if s == None:
        return ""
    # print "[str(options['base.time_format'])] ",[str(options['base.time_format'])]
    t = str2datetime_(s, [str(options['base.time_format'])])
    return t.strftime(str(options['base.time_format']))


# class ZBaseDateWidget(forms.TextInput):
#    class Media:
#            js = zbase_media+(MEDIA_URL+"/jslib/dwz.core.js",MEDIA_URL+"/jslib/dwz.datepicker.js",MEDIA_URL+"/jslib/dwz.ui.js",)
#            css = {
#                    'all': zbase_css+(MEDIA_URL+"/css/core.css",),
#            }
#    def __init__(self, attrs={}):
#            attrs.update({'class': 'date', 'dateFmt':'yyyy-MM-dd HH:mm:ss',})
#            super(ZBaseDateWidget, self).__init__(attrs=attrs)
#    def render(self, name, data, attrs=None):
#            self.attrs.update(attrs)
#            ret=super(ZBaseDateWidget, self).render(name, data, attrs=self.attrs)+\
#            u'''
#                        <a class='inputDateButton' href='javascript:void(0);'>选择</a>
#            '''
#            return ret
#    def value_from_datadict(self, data, files, name):
#            value = data.get(name, None)
#            if not value: return value
#            return str2date(value)

# class ZBaseTimeWidget2(forms.TextInput):  #该控件用于显示短格式（HH:MM）的时间显示/编辑
#    def __init__(self, attrs={}):
#            attrs.update({'class': 'wZBaseTime2Field', 'size': '5','maxlength':'8'}) #设定控件的html属性
#            super(ZBaseTimeWidget2, self).__init__(attrs=attrs)
#    def render(self, name, data, attrs=None):                                        #定义其显示的方法
#            self.attrs.update(attrs)
#            ret=super(ZBaseTimeWidget2, self).render(name, ("%s"%data)[:5], attrs=self.attrs) #取格式化后的前5个字符即可
#            return ret
# 由于HH:MM格式的字符串可以直接转化成日期，所以这个控件不需要相关的取值转换函数


class ZReadOnlyWidget(forms.TextInput):
    def __init__(self, attrs={}):
        super(ZReadOnlyWidget, self).__init__(attrs=attrs)

    def value_from_datadict(self, data, files, name):
        value = data.getlist(name)
        if not value: return None
        multiple = False
        if hasattr(self, "choices") and isinstance(self.choices, forms.models.ModelChoiceIterator):
            # value=[self.choices.queryset.get(pk=item) for item in value]
            if isinstance(self.choices.field, forms.models.ModelMultipleChoiceField):
                multiple = True
        if not multiple:
            value = value[0]
        # print "value_from_datadict", value, name
        return value

    def render(self, name, data, attrs=None):
        try:
            self.attrs.update(attrs)
            # print data
            if hasattr(self, "choices"):
                if hasattr(self.choices, "queryset"):
                    # print self.choices.queryset
                    if type(data) == list:
                        display = "<br>".join([u"%s" % self.choices.queryset.get(pk=item) for item in data])
                        display2 = "\n".join(
                            [u"<input value=\"%s\", name=\"%s\" type=\"hidden\" />" % (item, name) for item in data])
                        return u"""<div  style=\"height:60px;overflow-x:auto; overflow-y:scroll; border:1px solid #CAE2F9\"><ul><li>%s</li></ul></div>%s""" % (
                        display, display2)
                    display = self.choices.queryset.get(pk=data)
                else:
                    display = u"%s" % (dict(self.choices)[data])
                return super(ZReadOnlyWidget, self).render('', display, attrs=self.attrs) + \
                       (u'<input name="%s" value="%s" type="hidden">' % (name, data))
        except:
            import traceback;
            traceback.print_exc()
        return u'<input name="%s" value="%s" readonly="readonly" >' % (name, data or "")


# class ZBaseTimeWidget(forms.TextInput):
#    class Media:
#            js = zbase_media+(MEDIA_URL+"/jslib/dwz.core.js",MEDIA_URL+"/jslib/dwz.datepicker.js",MEDIA_URL+"/jslib/dwz.ui.js",)
#            css = {
#                    'all': zbase_css+(MEDIA_URL+"/css/core.css",),
#            }
#    def __init__(self, attrs={}):
#            attrs.update({'class': 'date', 'dateFmt':'HH:mm:ss',})
#            super(ZBaseTimeWidget, self).__init__(attrs=attrs)
#    def value_from_datadict(self, data, files, name): #从提交的数据中提取出相应字段并转换为时间对象
#            value = data.get(name, None)
#            if not value: return value
#            return str2time(value)                
#    def render(self, name, data, attrs=None):
#            self.attrs.update(attrs)
#            if data==None:
#                data=""
#            else:
#                data=u"%s"%data
#            ret=super(ZBaseTimeWidget, self).render(name, data.split('.')[0], attrs=self.attrs)+\
#            u"""<a class='inputDateButton' href='javascript:void(0);'>选择</a>"""
##            u'&nbsp;&nbsp;&nbsp;<span class="pop_time"><a id="clocklink"><img src="%s/img/icon_clock.gif" alt="%s"/></a></span>'%(MEDIA_URL,_(u"时间"))
#            return ret

# class ZBaseDateTimeWidget(forms.TextInput):
##    class Media:
##            js = zbase_media+(MEDIA_URL+"/jslib/dwz.core.js",MEDIA_URL+"/jslib/dwz.datepicker.js",MEDIA_URL+"/jslib/dwz.ui.js",)
##            css = {
##                    'all': zbase_css+(MEDIA_URL+"/css/core.css",),
##            }
#
#    def __init__(self, attrs={}):
#            attrs.update({'class': 'date', 'dateFmt':'yyyy-MM-dd HH:mm:ss',})
#            super(ZBaseDateTimeWidget, self).__init__(attrs=attrs)
#    def value_from_datadict(self, data, files, name):
#            value = data.get(name, None)
#            if not value: return value
#            return str2datetime(value)
#    def render(self, name, data, attrs=None):
#            self.attrs.update(attrs)
#            ret=super(ZBaseDateTimeWidget, self).render(name, (u"%s"%(data or "")).split('.')[0], attrs=self.attrs)+\
#            u'''
#                        <a class='inputDateButton' href='javascript:void(0);'>选择</a>
#            '''
#            #            u'''<span class="pop_cal">
##                 <a id="calendarlink"><img src="%s/img/icon_calendar.gif" alt="%s"/></a>
##               </span> | 
##               <span class="pop_time"> 
##                 <a id="clocklink"><img src="%s/img/icon_clock.gif" alt="%s"/></a>
##               </span>
##            '''%(MEDIA_URL,_(u"日期"),MEDIA_URL,_(u"时间"))
#            return ret

class ZBaseDateTimeWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'date', 'format': 'yyyy-MM-dd HH:mm:ss', 'width': '140px'})
        super(ZBaseDateTimeWidget, self).__init__(attrs=attrs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if not value: return value
        return str2datetime(value)

    def render(self, name, data, attrs=None):
        self.attrs.update(attrs)
        final_attrs = self.attrs
        final_attrs['name'] = name
        if data:
            _value = str(data)[:19]
        else:
            _value = ""
        ret_str = u'''
            <input %s value="%s" class="date" type="text" />
            ''' % (flatatt(final_attrs), _value)
        return mark_safe(ret_str)


class ZBaseDateWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'date', 'format': 'yyyy-MM-dd',})
        super(ZBaseDateWidget, self).__init__(attrs=attrs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if not value: return value
        return str2date(value)

    def render(self, name, data, attrs=None):
        self.attrs.update(attrs)
        final_attrs = self.attrs
        final_attrs['name'] = name
        if data:
            _value = str(data)[:10]
        else:
            _value = ""
        ret_str = u'''
            <input %s value="%s" class="date" type="text" />
            ''' % (flatatt(final_attrs), _value)
        return mark_safe(ret_str)


class ZBaseTimeWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'date', 'format': 'HH:mm:ss',})
        super(ZBaseTimeWidget, self).__init__(attrs=attrs)

    def value_from_datadict(self, data, files, name):  # 从提交的数据中提取出相应字段并转换为时间对象
        value = data.get(name, None)
        if not value: return value
        return str2time(value)

    def render(self, name, data, attrs=None):
        self.attrs.update(attrs)
        final_attrs = self.attrs
        final_attrs['name'] = name
        if data:
            _value = str(data)
        else:
            _value = "00:00:00"
        ret_str = u'''
            <input %s value="%s" class="date" type="text" />
            ''' % (flatatt(final_attrs), _value)
        return mark_safe(ret_str)


class ZBaseTimeWidget2(forms.TextInput):  # 该控件用于显示短格式（HH:MM）的时间显示/编辑,暂时只有门禁在使用
    def __init__(self, attrs={}):
        super(ZBaseTimeWidget2, self).__init__(attrs=attrs)

    def render(self, name, data, attrs=None):
        self.attrs.update(attrs)
        final_attrs = self.attrs
        final_attrs['name'] = name
        if data:
            _value = str(data)
        else:
            _value = "00:00"
        ret_str = u'''
            <input %s value="%s" type="text" />
            ''' % (flatatt(final_attrs), _value)
        return mark_safe(ret_str)


class ZBaseFloat_abv_zero_Widget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseFloatField ', 'size': '3', 'maxlength': '3', 'max': 9.9, 'min': 0.1})
        super(ZBaseFloat_abv_zero_Widget, self).__init__(attrs=attrs)


class ZBaseIntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update(
            {'class': 'wZBaseIntegerField number', 'size': '12', 'maxlength': '12', 'max': 0xffffffff, 'min': 0x0})
        super(ZBaseIntegerWidget, self).__init__(attrs=attrs)


class ZBase5IntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '5', 'maxlength': '5', 'max': 65535, 'min': 1})
        super(ZBase5IntegerWidget, self).__init__(attrs=attrs)


class ZBase4IntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '4', 'maxlength': '4', 'max': 9999, 'min': 1})
        super(ZBase4IntegerWidget, self).__init__(attrs=attrs)


class ZBase3IntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '3', 'maxlength': '3', 'max': 999, 'min': 0})
        super(ZBase3IntegerWidget, self).__init__(attrs=attrs)


class ZBaseDayMinsIntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '4', 'maxlength': '4', 'max': 1440, 'min': 0})
        super(ZBaseDayMinsIntegerWidget, self).__init__(attrs=attrs)


class ZBaseHolidayIntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '2', 'maxlength': '2', 'max': 99, 'min': 0x1})
        super(ZBaseHolidayIntegerWidget, self).__init__(attrs=attrs)


class ZBaseSmallIntegerWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseIntegerField number', 'size': '2', 'maxlength': '2', 'max': 0xffff, 'min': 0x0})
        super(ZBaseSmallIntegerWidget, self).__init__(attrs=attrs)


class ZBaseFloatWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseFloatField ', 'size': '3', 'maxlength': '3', 'max': 9.9, 'min': 0.0})
        super(ZBaseFloatWidget, self).__init__(attrs=attrs)


class ZBaseMoneyWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseFloatField ', 'size': '8', 'maxlength': '8', 'max': 9999, 'min': 0.1})
        super(ZBaseMoneyWidget, self).__init__(attrs=attrs)


class ZBaseNormalFloatWidget(forms.TextInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseFloatField ', 'size': '4', 'maxlength': '4', 'max': 0xffffff, 'min': 0.0})
        super(ZBaseNormalFloatWidget, self).__init__(attrs=attrs)


class ZBaseColorWidget(forms.TextInput):
    class Media:
        js = zbase_media + (MEDIA_URL + "/jslib/ColorPicker.js",)
        pass

    def __init__(self, attrs={}):
        attrs.update({'class': 'wZBaseColorField', 'size': '7', 'readonly': 'readonly'})
        super(ZBaseColorWidget, self).__init__(attrs=attrs)

    def render(self, name, data, attrs=None):
        self.attrs.update(attrs)
        color = data and int(data) or 0
        ret = super(ZBaseColorWidget, self).render(name, data, attrs=self.attrs) + \
              u"""<a href='javascript:void(0)' style='margin-left:10px;' onclick="$(this).colorPicker({ setValue:'input[name=Color]' })">%s</a>""" % _(
                  u"请选择颜色")
        return ret


def object_to_li(queryset, selected_id, level, item_format=u'<li alt="%s" class="level_%s">%s%s</li>'):
    result = []
    for obj in queryset:
        result.append(item_format % (
            obj.pk == selected_id and ("%s\" selected=\"selected\"" % obj.pk) or obj.pk,
            level, obj, ""))
    return u"\n".join(result)


def object_tree_self(queryset, root_object, parent_field, level=0,
                     item_format=u'<li alt="%s" class="level_%s">%s%s</li>', folder_format=u"<ul>%s</ul>"):
    child_objs = []
    field = parent_field + "_id"
    root = root_object.pk
    for obj in queryset:
        if getattr(obj, field) == root: child_objs.append(obj)
    childen = u""
    if child_objs:
        res = u""
        new_level = level + 1
        for obj in child_objs:
            res += object_tree_self(queryset, obj, parent_field, level=new_level, item_format=item_format,
                                    folder_format=folder_format)
        childen = folder_format % res
    result = item_format % (root_object.pk, level, root_object, childen)
    return result


def object_tree(root_object, relation, level=0, item_format=u'<li alt="%s" class="level_%s">%s%s</li>',
                folder_format=u"<ul>%s</ul>"):
    child_objs = getattr(root_object, relation).all()
    childen = u""
    model = root_object.__class__
    if child_objs:
        res = u""
        new_level = level + 1
        for obj in child_objs:
            if obj.__class__ == model:
                res += object_tree(obj, relation, level=new_level, item_format=item_format, folder_format=folder_format)
            else:
                res += item_format % (obj.pk, new_level, obj, "")
        childen = folder_format % res
    result = item_format % (root_object.pk, level, root_object, childen)
    return result


class ERelationSelf(Exception): pass


def queryset_to_tree(queryset, child_model=None, level=0,
                     item_format=u'<li alt="%s" class="level_%s">%s%s</li>',
                     folder_format=u"<ul>%s</ul>"):
    model = queryset.model
    if not child_model: child_model = model
    field = None
    for rel in model._meta.get_all_related_objects():
        if rel.model == child_model:  # self relation
            field = rel.field.name
            var_name = rel.var_name + "_set"
            break
    if not field: raise ERelationSelf("Not a relation '%s' for model '%s'" % (child_model, model))
    tree = []
    queryset = list(queryset)
    for root in queryset:
        if model == child_model:
            try:
                test_p = root.parent
            except:
                root.parent = None
            if not getattr(root, field):  # real a root, it has no parent
                tree.append(folder_format % object_tree_self(queryset, root, field, level, item_format, folder_format))
        else:
            tree.append(object_tree(root, var_name, level, item_format, folder_format))
    if model == child_model:
        return u"\n".join(tree)
    else:
        return folder_format % ("\n".join(tree))


def queryset_group(queryset, parent=None, data=[]):
    from base.models import DataTranslation
    try:
        model = queryset.model
    except AttributeError:
        model = queryset[0].__class__
    parent_field_name, parent_field_name2 = parent, None
    if parent == None:
        if hasattr(model, "_group_field"):
            parent_field_name = model._group_field
    if not parent_field_name:
        for f in model._meta.fields:
            #                        print f, f.name
            if isinstance(f, models.ForeignKey):
                parent = f
                parent_field_name = f.name
                if f.rel.to != User: break;
    elif type(parent) in (type(""), type(u"")):
        try:
            parent = model._meta.get_field_by_name(parent)[0]
        except models.FieldDoesNotExist as e:
            try:
                parent_field_name, parent_field_name2 = parent.split(".")
            #                                print parent_field_name
            except ValueError:
                raise e
            parent = model._meta.get_field_by_name(parent_field_name)[0]
            #                        print parent
            if not isinstance(parent, models.ForeignKey):
                raise e
            #                        print parent_field_name2
            parent = parent.rel.to._meta.get_field_by_name(parent_field_name2)[0]
        #                        print parent

    roots = {}
    qs = queryset
    for obj in qs:
        if obj.pk in data:
            obj.selected = True
        #                print "-------------------------------"
        #                print obj
        #                print parent_field_name
        value = getattr(obj, parent_field_name)
        #                print value
        if parent_field_name2:
            o = getattr(value, parent_field_name2)
            value = DataTranslation.get_field_display(ContentType.objects.get_for_model(value.__class__),
                                                      parent_field_name2, o)
        elif not isinstance(value, models.Model):
            value = DataTranslation.get_field_display(ContentType.objects.get_for_model(obj.__class__),
                                                      parent_field_name, value)
        if value not in roots:
            roots[value] = [obj, ]
        else:
            roots[value].append(obj)
    return roots


def queryset_group_to_tree(queryset, parent=None, level=0, item_format=u'<li alt="%s" class="level_%s">%s%s</li>',
                           folder_format=u"<ul>%s</ul>"):
    roots = queryset_group(queryset, parent)
    tree = []
    for root in roots:
        ret = object_to_li(roots[root], '', level + 1, item_format)
        children = folder_format % (ret)
        tree.append(item_format % (u"\" disabled=\"disabled\"", level, root, children))
    return u"\n".join(tree)


def get_content_type_list(queryset):
    from base import get_all_app_and_models
    apps = get_all_app_and_models()
    listTemp = []
    for k, v in apps.items():
        listTemp.append(u'<option class="level_0" disabled=disabled>%s</option>' % v["name"])
        for ms in v["models"]:
            m = ms["model"]
            if m:
                ct = ContentType.objects.get_for_model(m)
                if ct in queryset:
                    listTemp.append(u'<option value="%s" class="level_1">%s</option>' % (ct.pk, ms["verbose_name"]))
    return u'\n'.join(listTemp)


class ZBaseModelChoiceWidget(forms.Select):
    def __init__(self, attrs={}, choices=()):
        super(ZBaseModelChoiceWidget, self).__init__(attrs=attrs, choices=choices)

    def render_tree_self(self, name, data, attrs=None):
        final_attrs = self.attrs
        if self.attrs.get('no_load') and self.attrs['no_load']:
            if data:
                try:
                    verbos = self.choices.queryset.filter(pk=data)[0]
                except:
                    verbos = ''
                ret = u'<select %s> <option value="%s">%s</option></select>' % (flatatt(final_attrs), data, verbos)
            else:
                ret = u"<select %s> </select>" % flatatt(final_attrs)
        else:
            ret = u"<select %s>" % flatatt(final_attrs) + \
                  u'<option value="" class="level_0" id="id_null"><div>---------</div></option>' + \
                  queryset_to_tree(self.choices.queryset,
                                   item_format=u'<option value="%s" class="level_%s">%s</option>%s',
                                   folder_format=u"%s"
                                   ) + u"</select>"
        if not data == None:
            ret += u"<script>$('#%s option[value=%s]').attr('selected', 'selected')</script>" % (self.attrs['id'], data)
        return mark_safe(ret)

    def render_tree(self, name, data, attrs=None):
        final_attrs = self.attrs
        ret = u"<select %s>" % flatatt(final_attrs) + \
              u'<option value="" class="level_0" id="id_null"><div>---------</div></option>' + \
              queryset_group_to_tree(self.choices.queryset,
                                     item_format=u'<option value="%s" class="level_%s">%s</option>%s',
                                     folder_format=u"%s"
                                     ) + u"</select>"
        if not data == None:
            ret += u"<script>$('#%s option[value=%s]').attr('selected', 'selected')</script>" % (self.attrs['id'], data)
        return mark_safe(ret)

    def render_content_type(self, name, data, attrs=None):
        final_attrs = self.attrs
        ret = u"<select %s>" % flatatt(final_attrs) + \
              u'<option value="" class="level_0" id="id_null"><div>---------</div></option>' + \
              get_content_type_list(self.choices.queryset) \
              + u"</select>"
        if not data == None:
            ret += u"<script>$('#%s option[value=%s]').attr('selected', 'selected')</script>" % (self.attrs['id'], data)
        return mark_safe(ret)

    def render(self, name, data, attrs=None):
        if attrs: self.attrs.update(attrs)
        if 'id' not in self.attrs: self.attrs['id'] = 'id_' + name
        self.attrs = self.build_attrs(self.attrs, name=name)
        if self.choices.queryset.model == ContentType:
            try:
                return self.render_content_type(name, data, attrs)
            except Exception:
                import traceback;
                traceback.print_exc()
        try:
            return self.render_tree_self(name, data, attrs)
        except ERelationSelf:
            try:
                return self.render_tree(name, data, attrs)
            #                        except TypeError:
            #                                return super(ZBaseModelChoiceWidget, self).render(name,data,attrs)
            except Exception:
                # import traceback; traceback.print_exc()
                return super(ZBaseModelChoiceWidget, self).render(name, data, attrs)
        except:
            import traceback;
            traceback.print_exc()


def queryset_group_to_tab(queryset, parent=None, name='', attrs=''):
    """
    """
    item_format = u'<option value="%s" class="level_%s">%s</option>%s'
    folder_format = u"%s"
    if parent and len(parent) > 0 and (type(parent) in (type((1,)), type([1, ]))):
        parent1, parent2 = parent
    else:
        parent1, parent2 = parent, None
    roots = queryset_group(queryset, parent1)
    tab = []
    tree = []
    index = 1
    for root in roots:
        id = "%s_%s" % (queryset.model.__name__, index)
        tab.append(u"<li><a href='#id_tab_%s'>%s</li>" % (id, root))

        if parent2:
            ret = queryset_group_to_tree(roots[root], parent2, 1, item_format, folder_format)
        else:
            ret = object_to_li(roots[root], '', 1, item_format)
        children = folder_format % (ret)
        tree.append(u"<div id='id_tab_%s'><p><select name='%s' multiple='multiple' size='5'>%s</select></p></div>" % (
        id, name or id, children))
        index += 1
    return u"<div %s> <ul>%s</ul>%s</div>" % (attrs, u"\n".join(tab), u"\n".join(tree))


def queryset_group_to_accordion(queryset, parent=None, name='', attrs=''):
    """
    """
    item_format = u'<option value="%s" class="level_%s">%s</option>%s'
    folder_format = u"%s"
    if parent and len(parent) > 0 and (type(parent) in (type((1,)), type([1, ]))):
        parent1, parent2 = parent
    else:
        parent1, parent2 = parent, None
    roots = queryset_group(queryset, parent1)
    tab = []
    tree = []
    index = 1
    for root in roots:
        id = "%s_%s" % (queryset.model.__name__, index)

        if parent2:
            ret = queryset_group_to_tree(roots[root], parent2, 1, item_format, folder_format)
        else:
            ret = object_to_li(roots[root], '', 1, item_format)
        tree.append(
            u"<h3><a href='javascript:void(0)'>%s</h3><div><select name='%s' multiple='multiple' size='5'>%s</select></div>" % (
            root, name or id, ret))
        index += 1
    return u"<div %s>%s</div>" % (attrs, u"\n".join(tree))

    #        id="%s_%s"%(queryset.model.__name__,index)
    #        tab.append(u"<li><a href='#id_tab_%s'>%s</li>"%(id, root))
    #        item_format=u'<option value="%s" class="level_%s">%s</option>%s' 
    #        tree.append(u"<div id='id_tab_%s'><p><select name='%s' multiple='multiple' size='5'>%s</select></p></div>"%(id, name or id, children))


'''
default_permission_template="""
{% autoescape off %}<div {{ attrs }}><ul>{% for label, app in apps.items %}<li><a href='#id_tab_{{ label }}'>{{ app.name }}</li>{% endfor %}</ul>
    {% for label, app in apps.items %}
    <div id='id_tab_{{ label }}'><select name='{{ name }}' multiple='multiple' size='5'>
    {% for model in app.models %}
            <option value='' class='level_0' disabled='disabled'><img src='' />{{ model.verbose_name }} </option>
            {% for permission in model.permissions %}
                    <option value='{{ permission.pk }}' class='level_1'>{{ permission }} </option>
            {% endfor %}
    {% endfor %}
    </select></div>
    {% endfor %}
    </div>{% endautoescape %}
"""
'''

'''
default_permission_template="""
{% autoescape off %}
<script> 
    function selectck(sid){ 
            
            
            if ($("input[id^=\'"+sid+"\']:checkbox").attr('checked'))
                    $("input[id^=\'"+sid+"_\']:checkbox").attr("checked","checked")
            else
                    $("input[id^=\'"+sid+"_\']:checkbox").removeAttr("checked")
            
    }
</script>
<div {{ attrs }}>
    <ul class="tabs">
            {% for label, app in apps.items %}
                    <li><a href='#id_tab_{{ label }}' >{{ app.name }}</a></li>
            {% endfor %}
    </ul>
    {% for label, app in apps.items %}
    <div id='id_tab_{{ label }}' style='height:230px' >
            <ul name='' style="list-style-type:none;">
                    {% for model in app.models %}
                            <li value=''disabled='disabled' class='level_0'><input type='checkbox'   id ='{{ model.name }}' onclick="selectck(this.id)"   />&nbsp;&nbsp;{{ model.verbose_name }}</li>
                            {% for permission in model.permissions %}
                            <li value='{{ permission.pk }}' class='level_1' ><input type='checkbox'  {% if permission.selected %} checked='checked'  {% endif %}  name='permissions'  id ='{{ model.name }}_{{ permission.pk }}' value ='{{ permission.pk }}' />&nbsp;&nbsp;{{ permission }} </li>
                            {% endfor %}
                    {% endfor %}
            </ul>
    </div>
    {% endfor %}
</div>
{% endautoescape %}
"""
'''
default_permission_template = """
{% autoescape off %}
<script> 
    var models=[];
    var cfg_model=[];
    {% for label, app in apps %}
        {% for model in app.models %}
            {% if model.parent_model %}
             cfg_model=[];
             cfg_model.push("{{ model.parent_model }}");
             cfg_model.push("{{ model.name}}");
             cfg_model.push(
                "<li  id ='{{ model.name }}' {% if not model.model %} operation='{{ model.name }}' {% endif %} ><p class='t' >{{ model.verbose_name }}</p>"
                    +"<ul>"
                        +"{% for permission in model.permissions %}"
                        +"<li {% if model.hide_perms %}{% for hperm in model.hide_perms %}{% ifequal hperm permission.codename %}style='display:none'{% endifequal %}{% endfor %} {% endif %} {% if model.cancel_perms %}{% for ck,cv in model.cancel_perms %}{% ifequal cv permission.codename %}cancel_perms='{{ ck }}'{% endifequal %}{% endfor %}{% endif %} relate_perms='"
                           +"{% if model.select_related_perms %}"
                                +"{% for k,v in model.select_related_perms.items %}"
                                    +"{% ifequal k permission.codename %}{{v}}{% endifequal %}"
                                +"{%endfor%}"
                            +"{% endif %}"
                        +"'>{% if permission.selected %}<p class='t s' permission_code='{{permission.codename}}'>{% else %}<p class='t' permission_code='{{permission.codename}}'>{% endif %}<input class='displayN' type='checkbox'  {% if permission.selected %} checked='checked'  {% endif %}  name='permissions'  id ='{{ model.name }}_{{ permission.pk }}' value ='{{ permission.pk }}' />{{ permission }} </p></li>"
                        +"{% endfor %}"
                    +"</ul>"
                +"</li>");
              models.push(cfg_model);
            {% endif %}
        {% endfor %}
    {% endfor %}
    insert_tree_html(models);
    //remove_single_perm_node($(".filetree"));
    $(".filetree").treeview({collapsed: true});
    selectck();
</script>
<div {{ attrs }}>
    <ul class="tabs">
            {% for label, app in apps %}
                    <li><a href='#id_tab_{{ label }}' >{{ app.name }}</a></li>
            {% endfor %}
    </ul>
    {% for label, app in apps %}
    <div id='id_tab_{{ label }}' style='height:230px;overflow:auto;' >
            <ul class='filetree' style="list-style-type:none;">
                <li class='root_node'><p class='t'>{{ app.name }}</p>
                    <ul>
                        {% for model in app.models %}
                            {% if not model.parent_model %}
                                <li id ='{{ model.name }}' {% if not model.model %} operation='{{model.name}}' {% endif %}>
                                <p class='t'>{{ model.verbose_name }}</p>
                                    <ul>
                                        {% for permission in model.permissions %}
                                        <li     {% if model.hide_perms %}
                                                    {% for hperm in model.hide_perms %}
                                                        {% ifequal hperm permission.codename %}
                                                        style='display:none'
                                                        {% endifequal %}
                                                    {% endfor %} 
                                                {% endif %} 
                                                {% if model.cancel_perms %}
                                                    {% for ck,cv in model.cancel_perms %}
                                                        {% ifequal cv permission.codename %}
                                                            cancel_perms='{{ ck }}'
                                                        {% endifequal %}
                                                    {% endfor %}
                                                {% endif %} 
                                                relate_perms='
                                                {% if model.select_related_perms %}
                                                    {% for k,v in model.select_related_perms.items %}
                                                       {% ifequal k permission.codename %}{{v}}{% endifequal %}
                                                    {%endfor%}
                                                {% endif %}
                                        '>{% if permission.selected %}<p class='t s' permission_code='{{permission.codename}}'>{% else %}<p class='t' permission_code='{{permission.codename}}'>{% endif %}<input class='displayN' type='checkbox'  {% if permission.selected %} checked='checked'  {% endif %}  name='permissions'  id ='{{ model.name }}_{{ permission.pk }}' value ='{{ permission.pk }}' />{{ permission }} </p></li>
                                        {% endfor %}
                                    </ul>
                                </li>
                            {% endif %}
                        {% endfor %}
                    </ul>
                </li>
            </ul>
    </div>
    {% endfor %}
</div>
{% endautoescape %}
"""


def permission_render(queryset, name='', attrs='', data=None):
    from base import get_all_permissions
    try:
        t = loader.select_template(["permission_widget.html"])
    except TemplateDoesNotExist:
        t = Template(default_permission_template)
    apps = get_all_permissions(queryset)
    try:
        for label, app in apps:
            for model in app["models"]:
                for permission in model["permissions"]:
                    if data:
                        if permission.pk in data:
                            permission.selected = True
                        else:
                            permission.selected = False
                    else:
                        permission.selected = False
    except:
        import traceback;
        traceback.print_exc()
    return t.render(Context({'apps': apps, 'name': name, 'attrs': attrs}))


default_select_multiple_template_original = ("""
{% autoescape off %}
    {% for item in queryset %}
            <li value='{{ item.pk }}' class='level_1' ><input type='checkbox'  {% if item.selected %} checked='checked'  {% endif %}  name='{{ name }}'  id ='id_{{ name }}_{{ id }}_{{ item.pk }}' value ='{{ item.pk }}' />&nbsp;&nbsp;{{ item }} </li>
    {% endfor %}
{% endautoescape %}
""",
                                             """
<script> 
    function selectck(sid){ 
            if ($("input[id^=\'"+sid+"\']:checkbox").attr('checked'))
                    $("input[id^=\'"+sid+"_\']:checkbox").attr("checked","checked")
            else
                    $("input[id^=\'"+sid+"_\']:checkbox").removeAttr("checked")
    }
</script>
{% autoescape off %}
<div {{ attrs }}>
{% endautoescape %}
{% if roots.items %}
<ul class='filetree' name='' style="list-style-type:none;">    
    {% for root,content in roots.items %}
            <li class='level_0'><input type='checkbox' id ='id_{{ name }}_{{ root.pk }}' onclick="selectck(this.id)" />{{ root }}</li>
            {{ content }}
    {% endfor %}        
</ul>
{% else %}
            <ul style="color:red">{{ error }}</ul>
{% endif %}
</div>
"""
                                             )


def queryset_render_multiple_original(queryset, name, attr_str, data, parent=None):
    try:
        t_item = loader.select_template(["select_multiple_widget_items_original.html"])
    except TemplateDoesNotExist:
        t_item = Template(default_select_multiple_template_original[0])
    try:
        t = loader.select_template(["select_multiple_widget_original.html"])
    except TemplateDoesNotExist:
        t = Template(default_select_multiple_template_original[1])

    if parent and len(parent) > 0 and (type(parent) in (type((1,)), type([1, ]))):
        parent1, parent2 = name
    else:
        parent1, parent2 = parent, None
    if data == None: data = []  # 当新增数据时，执行此语句
    roots = queryset_group(queryset, parent1, data)

    # 多对多多选框没有内容可以显示时，显示返回模型中Admin类中定义的报错信息
    rootserror = ''
    if roots == {}:
        model = queryset.model
        if hasattr(model.Admin, "blankerror_text"):
            rootserror = model.Admin.blankerror_text

    return t.render(
        Context({'roots':
                     dict([(root, t_item.render(Context({'queryset': value,
                                                         'id': root and root.pk or "",
                                                         'name': name,
                                                         'attrs': attr_str}))) for root, value in roots.items()]),
                 'name': name, 'attrs': attr_str, 'error': rootserror}
                )
    )


# 多对多字段的默认控件
default_select_multiple_template = ("""
{% autoescape off %}
    <script>
    //remove_single_perm_node($("#"+"{{ id }}"+" .filetree"));
    $("#"+"{{ id }}"+" .filetree").treeview();
    check_root("{{ id }}"); 
    check_selected("{{ id }}");  
    </script>

    <div {{ attrs }} style='height:230px'>
    {% if roots.items %}
    <ul class='filetree' style="list-style-type:none;">
        <li id='id_all' class='root_node collapsable lastCollapsable'><p class='t'>{{ all }}</p>
        <ul>
        {% for root, queryset in roots.items %} 
        
            <li id='id_root_{{ module_name }}_{{ root.pk }}' class ='root_node collapsable lastCollapsable'><p class='t'>{{ root }}</p>
                <ul>
                    {% for item in queryset %}
                        <li>
                        {% if item.selected %}<p class='t s'>{% else %}<p class='t'>{% endif %}<input class='displayN' type='checkbox'  {% if item.selected %} checked='checked' {% endif %}  name='{{ name}}'  id ='id_{{ item.pk }}' value ='{{ item.pk }}' />{{ item }} </p>
                        </li>
                    {% endfor %}
                </ul>
            </li>
        
        {% endfor %}
        </ul>
        </li>
    </ul>
    </div>
    {% else %}
        <ul style="color:red">{{ error }}</ul>
    {% endif %}
    </div>
    
{% endautoescape %}

"""
                                    )


def queryset_render_multiple(queryset, name, attr_str, data, id, parent=None):
    try:
        t = loader.select_template(["select_multiple_widget.html"])
    except TemplateDoesNotExist:
        t = Template(default_select_multiple_template)

    if parent and len(parent) > 0 and (type(parent) in (type((1,)), type([1, ]))):
        parent1, parent2 = name
    else:
        parent1, parent2 = parent, None
    if data == None: data = []  # 当新增数据时，执行此语句
    roots = queryset_group(queryset, parent1, data)

    # 多对多多选框没有内容可以显示时，显示返回模型中Admin类中定义的报错信息
    rootserror = ''
    module_name = ''
    if roots == {}:
        model = queryset.model
        if hasattr(model.Admin, "blankerror_text"):
            rootserror = model.Admin.blankerror_text
    else:
        # dealing with the selected items
        for root, queryset in roots.items():
            module_name = root._meta.module_name
            for item in queryset:
                if data:
                    if item.pk in data:
                        item.selected = True
                    else:
                        item.selected = False
                else:
                    item.selected = False

    return t.render(Context(
        {'roots': roots, 'name': name, 'attrs': attr_str, 'all': CHOOSE_ALL, 'module_name': module_name, 'id': id,
         'error': rootserror}))  # id为html标签的id


class DivCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def __init__(self, attrs={}, choices=()):
        super(DivCheckboxSelectMultiple, self).__init__(attrs=attrs, choices=choices)

    def render(self, name, data, attrs=None):
        if self.choices:
            self.choices.queryset = Group.objects.exclude(name__exact="role_for_employee")
        html = super(DivCheckboxSelectMultiple, self).render(name, data, attrs)
        html = "<div class='div_user_groups' id='id_%s' >" % name + html + "</div>"
        return html


class ZBaseModelMany2ManyWidget(forms.CheckboxSelectMultiple):
    def __init__(self, attrs={}, choices=()):
        super(ZBaseModelMany2ManyWidget, self).__init__(attrs=attrs, choices=choices)

    def render_tab(self, name, data, fields=(), attrs=None):
        final_attrs = self.attrs
        attr_str = flatatt(final_attrs)
        queryset = self.choices.queryset
        id = final_attrs['id']
        ret = queryset_group_to_tab(queryset, fields, final_attrs['name'], attr_str) + \
              (u"<script>$(\"div.wZBaseManyToManyField#%s\").tabs(); %s; </script>" % (id, ""))
        return mark_safe(ret)

    def render_acc(self, name, data, attrs=None):
        final_attrs = self.attrs
        attr_str = flatatt(final_attrs)
        queryset = self.choices.queryset
        id = final_attrs['id']
        ret = queryset_group_to_accordion(queryset, ('content_type.app_label', 'content_type'), final_attrs['name'],
                                          attr_str) + \
              (u"<script>$(\"div.#%s\").accordion({collapsible: true}); %s; </script>" % (id,
                                                                                          data and (";".join([
                                                                                                                 "$('#%s option[value=%s]').attr('selected', 'selected')" % (
                                                                                                                 id, d)
                                                                                                                 for d
                                                                                                                 in
                                                                                                                 data])) or ""))
        return mark_safe(ret)

    def render_permission(self, name, data, attrs=None):
        queryset = self.choices.queryset
        if not (queryset.model == Permission): return None
        final_attrs = self.attrs
        attr_str = flatatt(final_attrs)
        id = final_attrs['id']
        ret = permission_render(queryset, name, attr_str, data) + \
              (u"<script>$(\"div.wZBaseManyToManyField#%s\").tabs(\"#id_permissions > div\"); %s; </script>" % (id,
                                                                                                                data and (
                                                                                                                ";".join(
                                                                                                                    [
                                                                                                                        "$('#%s option[value=%s]').attr('selected', 'selected')" % (
                                                                                                                        id,
                                                                                                                        d)
                                                                                                                        for
                                                                                                                        d
                                                                                                                        in
                                                                                                                        data])) or ""))
        return mark_safe(ret)

    def render_checkbox(self, name, data):
        queryset = self.choices.queryset
        final_attrs = self.attrs
        attr_str = flatatt(final_attrs)
        id = final_attrs['id']
        # from mysite.personnel.models import Employee
        # if queryset.model == Employee: #选人控件不需要此多对多控件（暂针对权限组的特殊情况）。
        # return queryset_render_multiple_original(queryset, name, attr_str, data)
        ret = queryset_render_multiple(queryset, name, attr_str, data, id)
        return mark_safe(ret)

    def render(self, name, data, attrs=None):
        if attrs: self.attrs.update(attrs)
        if 'id' not in self.attrs: self.attrs['id'] = 'id_' + name
        self.attrs = self.build_attrs(self.attrs, name=name)
        ret = self.render_permission(name, data, attrs)
        if ret: return ret

        try:
            return self.render_tab(name, data, ('content_type.app_label', 'content_type'))
        except:
            pass
        try:
            return self.render_checkbox(name, data)
        except TypeError:
            return super(ZBaseModelMany2ManyWidget, self).render(name, data, attrs)
        except:
            import traceback;
            traceback.print_exc()
            return super(ZBaseModelMany2ManyWidget, self).render(name, data, attrs)

    class Media:
        pass


def label_tag(self, contents=None, attrs=None):
    """
    new label_tag for "required class label.
    """
    new_attrs = {}
    if self.field.required:
        new_attrs['class'] = 'required'
    if attrs:
        new_attrs.update(attrs)
    return label_tag.old_label_tag(self, contents, new_attrs)


if not hasattr(label_tag, "old_label_tag"):
    label_tag.old_label_tag = forms.forms.BoundField.label_tag
    forms.forms.BoundField.label_tag = label_tag


def permission__unicode__(self):
    """ 
    new __unicode__ function of Permission for i18n 
    """
    try:
        return _(self.name)
    except:
        import traceback;
        traceback.print_exc()
        return self.name


# if not hasattr(Permission.__unicode__, "old_fun"):
#     permission__unicode__.old_fun = Permission.__unicode__
#     Permission.__unicode__ = permission__unicode__
#     Permission._meta.ordering = ('content_type__app_label', 'content_type', 'codename')

# WIDGET_FOR_DBFIELD_DEFAULTS = {
#     # models.SmallIntegerField:ZBaseSmallIntegerWidget,
#     # models.IntegerField:    ZBaseIntegerWidget,
#     models.DateTimeField: ZBaseDateTimeWidget,
#     models.DateField: ZBaseDateWidget,
#     models.TimeField: ZBaseTimeWidget,
#     TimeField2: ZBaseTimeWidget2,
#     ColorField: ZBaseColorWidget,
#     models.ForeignKey: ZBaseModelChoiceWidget,
#     models.OneToOneField: ZBaseModelChoiceWidget,
#     models.ManyToManyField: ZBaseModelMany2ManyWidget,
#     ZManyToManyField.old_m2m: ZBaseModelMany2ManyWidget,
# }


def check_limit(f, model, formfield, instance=None, level_type=0):
    from django.db.models import Q
    if hasattr(formfield, "queryset"):
        lname = "limit_%s_to" % f.name
        # print "---+++",f.name,"+++",level_type
        if hasattr(model, lname):
            try:
                try:
                    if f.name == "door_group" or f.name == "level_timeseg":
                        # print"_____here1"
                        formfield.queryset = formfield.queryset.complex_filter(
                            instance or getattr(model(), lname)(level_type) or Q())
                    else:
                        formfield.queryset = formfield.queryset.complex_filter(
                            instance or getattr(model(), lname)() or Q())
                except TypeError:
                    if f.name == "door_group" or f.name == "level_timeseg":
                        # print"_____here2"
                        formfield.queryset = getattr(instance or model(), lname)(formfield.queryset, level_type)
                    else:
                        formfield.queryset = getattr(instance or model(), lname)(formfield.queryset)
            except:
                import traceback;
                traceback.print_exc()
                pass


def form_field(f, **kwargs):
    if 'widget' not in kwargs:
        c = f.__class__
        while True:
            if c in WIDGET_FOR_DBFIELD_DEFAULTS:
                kwargs['widget'] = WIDGET_FOR_DBFIELD_DEFAULTS[c]
                # print f.name, kwargs, c, WIDGET_FOR_DBFIELD_DEFAULTS[c]
                break
            elif c.__base__:
                c = c.__base__
            else:
                break

            #  主要去掉model.meta.many_to_many的help_text,其它情况由base.models.ZManyToManyField处理
    if f.__class__ == ZManyToManyField.old_m2m:
        f.help_text = ""
    ret = f.formfield(**kwargs)
    if ret:
        #            for v in f.validators:
        #                if v not in ret.validators: ret.validators.append(v)
        attrs = ret.widget.attrs
        if 'class' not in attrs:
            attrs['class'] = 'wZBase' + f.__class__.__name__
        if ret.required:
            ret.widget.attrs['class'] += ' required'
        if isinstance(f, models.ForeignKey):
            ret.widget.attrs['class'] += ' zd_' + f.rel.to.__name__
        #        print f, kwargs
    return ret


def form_field_readonly(f, **kwargs):
    kwargs.update({'widget': ZReadOnlyWidget})
    ret = f.formfield(**kwargs)
    # print "form_field_readonly: f=", f
    # print "form_field_readonly: ret=", ret
    # print "form_field_readonly: kwargs=", kwargs
    if ret:
        attrs = ret.widget.attrs
        attrs.update({'readonly': 'true'})
        if 'class' not in attrs:
            attrs['class'] = 'wZBase' + f.__class__.__name__
        if ret.required:
            ret.widget.attrs['class'] += ' required'
        if isinstance(f, models.ForeignKey):
            ret.widget.attrs['class'] += ' zd_' + f.rel.to.__name__

    return ret


def test():
    print(queryset_group_to_tab(Permission.objects.all()[:2], ('content_type.app_label', 'content_type')))


if __name__ == "__main__":
    # test()
    pass

# class ZBaseCheckNoWidget(forms.TextInput):
#        
#        def __init__(self, attrs={}):
#                #attrs.update({'class': 'wZBaseIntegerField number', 'size': '12', 'max': 0xffffffff})
#                super(ZBaseCheckNoWidget, self).__init__(attrs=attrs)
#        def render(self, name, data, attrs=None):
#                from dbapp.urls import dbapp_url
#                
#                self.attrs.update(attrs)
#                ret=super(ZBaseCheckNoWidget, self).render(name, (u"%s"%(data or "")).split('.')[0], attrs=self.attrs)+\
#                '<a onclick="wgCheckNo(%s,%s)">%s</a><div id="div_id%s"></div>'%( 
#                                dbapp_url+",_("time"))
#                return ret
#        

import string

nums = string.digits


# 根据传入的人员编号和数据库记录进行匹配，有效记录记入list_append,没有匹配出来则认为
# 是错误数据，提示用户，记入list_drop，忽略非数字的记录--王昌胜--2011-11-29
def add_list(recode_userinfo, data_column, list_append, list_drop):
    item = str(data_column)
    for i in item:
        if i not in nums:  # 非数字则不处理
            return
    flag = 0
    data_column_append_zero = "%09d" % int(data_column)  # 为数字补零
    for ele in recode_userinfo:
        if ele[0] == data_column_append_zero:  # 有效数据，加入插入链表
            list_append.append(ele[1])
            flag = 1
            break
    if flag == 0:
        list_drop.append(data_column)  # 无效数据，提示用户
    return


# 传入上传文件流，返回需要添加的数据，并提示无效数据--王昌胜--2011-11-29
def get_list_from_file(upload_file):  # 传入文件流，返回需要添加数据的链表
    from django.db import connection
    from dbapp.importandexport import ParseXlsUxlrd
    from django.conf import settings
    uploadpath = settings.ADDITION_FILE_ROOT + "/"
    sql = "select badgenumber,userid from userinfo"  # 进行校验的数据库字段放在第一位
    cursor = connection.cursor()
    cursor.execute(sql)
    recode_userinfo = cursor.fetchall()
    list_append = []
    list_drop = []
    file_name = str(upload_file)
    if file_name:
        file_type = file_name.split('.')[1]
        if file_type == 'txt' or file_type == 'csv':
            try:
                file_stream = upload_file.file
                reader = file_stream.readline()
                while reader != "":
                    line_data = ""
                    if reader.endswith("\r\n"):
                        reader = reader[:len(reader) - 2]
                        line_data = reader.split("\r\n")[0]
                    elif reader.endswith("\r"):
                        reader = reader[:len(reader) - 1]
                        line_data = rec.split("\r")[0]
                    elif reader.endswith("\n"):
                        reader = reader[:len(reader) - 1]
                        line_data = reader.split("\n")[0]
                    else:
                        # linedata = reader.split(" ")[0]
                        line_data = reader
                    data_column = str(line_data.split(" ")[0])  # 第一列数据
                    if data_column:
                        add_list(recode_userinfo, data_column, list_append, list_drop)
                    reader = file_stream.readline()
            except:
                raise Exception(_(u'上传文件解析失败,请重新检查上传文件,确保第一列为人员编号'))
            finally:
                file_stream.close()
                cursor.close()
                connection.close()
                # if list_drop:
                # raise Exception(_(u'没有找到人员编号为:%s的信息,请确认人员编号是否正确'%list_drop))
        elif file_type == 'xls':
            try:
                file_path = uploadpath + file_name
                writer = file(file_path, "w+b", )
                line_data = upload_file.file.read()  # 一次读入所有信息
                writer.write(line_data)
                writer.close()
                ds = ParseXlsUxlrd(file_path)  # 调用解析excel文件到数组的函数
                for sh in range(len(ds)):
                    if len(ds[sh][1]) >= 0:
                        for row in range(0, len(ds[sh][1])):
                            data_column = ds[sh][1][row][0][1]
                            if data_column:
                                data_column = str(data_column).split('.')[0]
                                add_list(recode_userinfo, data_column, list_append, list_drop)
            except:
                raise Exception(_(u'上传文件解析失败,请重新检查上传文件,确保第一列为人员编号'))
            finally:
                import os
                if (os.path.isfile(file_path)):
                    os.remove(file_path)
                writer.close()
                cursor.close()
                connection.close()
                # if list_drop:
                # raise Exception(_(u'没有找到人员编号为:%s的信息,请确认人员编号是否正确'%list_drop))
        else:
            raise Exception(_(u'上传文件类型错误,必须为以下文件类型：xls/txt/csv'))
    return list_append


from django.db import connection


# 以查询数据库方式匹配人员编号是否合法--王昌胜--20111130
def add_list_old(data_column, list_append, list_drop):
    item = str(data_column)
    for i in item:
        if i not in nums:  # 非数字则不处理
            return
    data_column_append_zero = "%09d" % int(data_column)
    sql = "select badgenumber,userid from userinfo where badgenumber = '%s'" % (data_column_append_zero)
    cursor = connection.cursor()
    cursor.execute(sql)
    element = cursor.fetchall()
    if element:
        for it in element:
            if it[0] == data_column or it[0] == data_column_append_zero:  # 有效数据，加入插入链表
                list_append.append(it[0])
    else:
        list_drop.append(data_column)  # 无效数据，提示用户
    cursor.close()
    connection.close()
    return


# 以查询数据库方式匹配人员编号是否合法--王昌胜--20111130
def get_list_from_file_old(upload_file):  # 传入文件流，返回需要添加数据的链表
    from django.db import connection
    from dbapp.importandexport import ParseXlsUxlrd
    from django.conf import settings
    uploadpath = settings.ADDITION_FILE_ROOT + "/"
    # sql = "select badgenumber,userid from userinfo"  #进行校验的数据库字段放在第一位
    # cursor = connection.cursor()
    # cursor.execute(sql)
    # element = cursor.fetchall()
    list_append = []
    list_drop = []
    file_name = str(upload_file)
    if file_name:
        file_type = file_name.split('.')[1]
        if file_type == 'txt' or file_type == 'csv':
            try:
                file_stream = upload_file.file
                reader = file_stream.readline()
                while reader != "":
                    line_data = ""
                    if reader.endswith("\r\n"):
                        reader = reader[:len(reader) - 2]
                        line_data = reader.split("\r\n")[0]
                    elif reader.endswith("\r"):
                        reader = reader[:len(reader) - 1]
                        line_data = rec.split("\r")[0]
                    elif reader.endswith("\n"):
                        reader = reader[:len(reader) - 1]
                        line_data = reader.split("\n")[0]
                    else:
                        # linedata = reader.split(" ")[0]
                        line_data = reader
                    data_column = str(line_data.split(" ")[0])  # 第一列数据
                    if data_column:
                        add_list_old(data_column, list_append, list_drop)
                    reader = file_stream.readline()
            except:
                raise Exception(_(u'上传文件解析失败,请重新检查上传文件,确保第一列为人员编号'))
            finally:
                file_stream.close()
                cursor.close()
                connection.close()
                if list_drop:
                    raise Exception(_(u'没有找到人员编号为:%s的信息,请确认人员编号是否正确' % list_drop))
        elif file_type == 'xls':
            try:
                file_path = uploadpath + file_name
                writer = file(file_path, "w+b", )
                line_data = upload_file.file.read()  # 一次读入所有信息
                writer.write(line_data)
                writer.close()
                ds = ParseXlsUxlrd(file_path)  # 调用解析excel文件到数组的函数
                for sh in range(len(ds)):
                    if len(ds[sh][1]) >= 0:
                        for row in range(0, len(ds[sh][1])):
                            data_column = ds[sh][1][row][0][1]
                            if data_column:
                                data_column = str(data_column).split('.')[0]
                                add_list_old(data_column, list_append, list_drop)
            except:
                raise Exception(_(u'上传文件解析失败,请重新检查上传文件,确保第一列为人员编号'))
            finally:
                import os
                os.remove(file_path)
                writer.close()
                # cursor.close()
                # connection.close()
                if list_drop:
                    raise Exception(_(u'没有找到人员编号为:%s的信息,请确认人员编号是否正确' % list_drop))
        else:
            raise Exception(_(u'上传文件类型错误,请上传文件类型必须为以下类型：xls/txt/csv'))
    return list_append
