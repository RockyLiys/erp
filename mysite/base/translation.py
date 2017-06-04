# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.functional import lazy
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

from mysite.base.cached_model import CachingModel

CACHE_PREFIX = settings.CACHE_MIDDLEWARE_KEY_PREFIX
CACHE_EXPIRE = 60 * 60 * 24


class DataTranslation(CachingModel):
    # 定义数据项的多国语言显示
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    property = models.CharField(max_length=100)
    language = models.CharField(max_length=10)
    value = models.CharField(max_length=200)
    display = models.CharField(max_length=400)

    class Admin(CachingModel.Admin):
        visible = False
        menu_index = 600

    def __unicode__(self):
        return u"[%s] %s.%s: %s -> %s" % (
        self.language, self.content_type.name, self.property, self.value, self.display)

    @classmethod
    def get_cache_key(self, content_type, field_name, value, language):
        return ("%s.trans.%s.%s.%s.%s" % (CACHE_PREFIX, content_type.pk, field_name, value, language)).replace(" ", "_")

    @classmethod
    def get_field_display(self, model, field_name, value, language=None):
        ct = ContentType.objects.get_for_model(model)
        if value:  # 该字段不是空值
            try:
                if not language:  # 没有传入语言参数，取当前请求
                    language = translation.get_language()
                # print "language:", language
                if not language: return value
                key = self.get_cache_key(ct, field_name, value, language)
                value2 = cache.get(key)
                if value2 == None:
                    try:
                        value2 = self.objects.get(content_type=ct, property=field_name, language=language,
                                                  value=value).display
                    except ObjectDoesNotExist as e:
                        if "_" in language:
                            value2 = self.objects.get(content_type=ct, property=field_name,
                                                      language=language.split("_")[0], value=value).display
                        else:
                            raise e
                    if value2 != None:
                        cache.set(key, value2, CACHE_EXPIRE)
                if value2: return value2
            except ObjectDoesNotExist:
                # 写入表中等待翻译
                self(content_type=ct, property=field_name, language=language, value=value, display=value).save()
                cache.set(key, value2, CACHE_EXPIRE)
        return value

    @classmethod
    def get_obj_display(self, obj, field_name, language=None):
        model = obj.__class__
        value = getattr(obj, field_name)
        return self.get_field_display(model, field_name, value, language)

    @classmethod
    def get_obj_display2(self, obj, field_name, language=None):
        model = obj.__class__
        value = getattr(obj, field_name)
        s = self.get_field_display(model, field_name, value, language)
        if s == value:
            return translation.ugettext(s)
        return value

    class Meta:
        verbose_name = translation.ugettext_lazy(u"翻译为数据")


class StrTranslation(CachingModel):
    '''定义字符串资源的多国语言显示'''
    str = models.ForeignKey("StrResource")
    language = models.CharField(max_length=10)
    display = models.CharField(max_length=400)

    class Admin(CachingModel.Admin):
        menu_index = 600
        visible = False

    def __unicode__(self):
        return u"[%s] %s -> %s" % (self.language, self.str, self.display)

    class Meta:
        verbose_name = translation.ugettext_lazy(u"翻译为字符串资源")


class StrResource(CachingModel):
    '''
    定义系统中用到的字符串资源
    '''
    app = models.CharField(max_length=20, null=True, blank=True)  # 应用
    str = models.CharField(max_length=400)  # 字符串资源

    class Admin(CachingModel.Admin):
        log = False
        cache = 20 * 24 * 60 * 60  # 20day才过期
        visible = False

    def __unicode__(self):
        if self.app:
            return u"[%s] %s" % (self.app, self.str)
        else:
            return unicode(self.str)

    def get_display(self, language):
        try:
            if not language:  # 没有传入语言参数，取当前请求
                language = translation.get_language()
            label = StrTranslation.objects.get(str__id=self.pk, language=language).display
            if label: return label
        except Exception as e:
            print(self.str, language)
            print(e)
        return self.str

    @classmethod
    def get_cache_key(self, app, value, language):
        return cache.get("%s.strres.%s.%s.%s"(CACHE_PREFIX, app, value, language))

    @classmethod
    def get_app_text(self, app, str, language=None):
        try:
            obj = self.objects.get(app=app, str=str)
            return obj.get_display(language)
        except:
            import traceback;
            traceback.print_exc()
            try:
                return self.objects.get(app=None, str=str).get_display(language)
            except:
                pass
        return unicode(str)

    @classmethod
    def get_text(self, str, language=None):
        try:
            return self.objects.get(app=None, str=str).get_display(language)
        except ObjectDoesNotExist:
            from django.conf import settings
            if settings.DEBUG:
                # 写入表中等待翻译
                self(app=None, str=str).save()
        return unicode(str)


def updateResTrans(str, res):
    try:
        r = StrResource.objects.get(app=None, str=str)
    except ObjectDoesNotExist:
        r = StrResource(app=None, str=str)
        r.save()
    except:
        return
    language = translation.get_language()
    try:
        t = StrTranslation.objects.get(str=r, language=language)
        if t.display == res: return
    except ObjectDoesNotExist:
        t = StrTranslation(str=r, language=language)
    t.display = res
    t.save()


def _ugettext__(str):
    '''
    _ugettext_，该函数先根据字符串的格式检查是否数据项，若是则进行数据项替换，
    否则，再检查字符串资源翻译表，若还是没有的话，调用原来的翻译函数.
    数据项格式为: ~应用名.模型名.字段名.需翻译的字符串
    '''
    if str.find('~') == 0:
        s = str[1:].split(".", 3)
        # print "_ugettext data", s
        try:
            model = models.get_model(s[0], s[1])
            str = DataTranslation.get_field_display(model, s[2], s[3])
            if str and not (str == s[3]):
                return str
        except:
            pass
    else:
        try:
            return translation.old_ugettext(str)
        except:
            return str
        #        elif False:
        s = str
        # print "_ugettext resource", s
        try:
            str = StrResource.get_text(s)
            if str and not (str == s):
                return str
        except Exception as e:
            # print e
            pass
    try:
        res = translation.old_ugettext(str)
        updateResTrans(str, res)
    except UnicodeDecodeError:
        return str
    return res


def _ugettext_(str):
    """
    cached _ugettext__ function
    """
    # return translation.ugettext(str)
    # language=translation.get_language()
    # key=u'%s:i18n:%s:%s' % (CACHE_PREFIX, language, str.replace(' ', '_'))
    # s=cache.get(key)
    # if s:
    #         return s
    try:
        s = _ugettext__(str)
    except:
        import traceback;
        traceback.print_exc()
        s = str
        # print "_ugettext_ not in cache: ", str, s
    #        cache.set(key, s, CACHE_EXPIRE)
    return s


# 检查并替换原来的国际化函数
if not (translation.ugettext.__doc__ == _ugettext_.__doc__):
    # print "install the new translation, ", translation.ugettext
    translation.old_ugettext = translation.ugettext
    translation.ugettext = _ugettext_
    _ = lazy(_ugettext_, str)
    translation.old_ugettext_lazy = translation.ugettext_lazy
    translation.ugettext_lazy = _
    pass

ugettext_lazy = lazy(_ugettext_)
