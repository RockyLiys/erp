#!/usr/bin/env python
#coding=utf-8

from django.db import models
from django.db.models import Q
from django.utils.encoding import smart_unicode, iri_to_uri
from django.utils.translation import ugettext as _
from django.utils.html import escape
from safestring import mark_safe
import datetime
from django.core.cache import cache

class FilterSpec(object):
        filter_specs = []
        def __init__(self, f, request, params, model):
                self.field = f
                self.params = params

        def register(cls, test, factory):
                cls.filter_specs.append((test, factory))
        register = classmethod(register)

        def create(cls, f, request, params, model):
                for test, factory in cls.filter_specs:
                        if test(f):
                                return factory(f, request, params, model)
        create = classmethod(create)

        def has_output(self):
                return True

        def choices(self, cl):
                raise NotImplementedError()

        def title(self):
                return self.field.verbose_name

        def fieldName(self):
                return self.field.name


class RelatedFilterSpec(FilterSpec):
        def __init__(self, f, request, params, model):
                super(RelatedFilterSpec, self).__init__(f, request, params, model)
                if isinstance(f, models.ManyToManyField):
                        self.lookup_title = f.rel.to._meta.verbose_name
                else:
                        self.lookup_title = f.verbose_name
                self.lookup_kwarg = '%s__%s__exact' % (f.name, f.rel.to._meta.pk.name)
                self.lookup_val = request.GET.get(self.lookup_kwarg, None)
                self.lookup_choices = f.rel.to.objects.all()
                self.model=f.rel.to
        def has_output(self):
                return True #len(self.lookup_choices) > 1

        def fieldName(self):
                return '%s__%s' % (self.field.name, self.field.rel.to._meta.pk.name)

        def title(self):
                return self.lookup_title

        def choices(self, cl):
                self.fCount=1
                yield {'selected': self.lookup_val is None,
                           'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
                           'display': _(u'所有')}
                cacheKey="dbapp_filter_"+self.lookup_kwarg
                theChoices=cache.get(cacheKey)
                if theChoices==None:
                        theChoices=list(self.lookup_choices[:21])
                        cache.set(cacheKey, theChoices, 60)
                for val in theChoices:
                        self.fCount+=1
                        if self.fCount>15:
                                break
                        pk_val = getattr(val, self.field.rel.to._meta.pk.attname)
                        yield {'selected': self.lookup_val == smart_unicode(pk_val),
                                   'query_string': cl.get_query_string({self.lookup_kwarg: pk_val}, ['p']),
                                   'display': val}
                if self.fCount>2:
                        ftitle=smart_unicode(_(u"过滤器通过%(title)s")%{'title':self.lookup_title})
                        yield {'selected': False,
                                'query_string': u"javascript:$.zk._data_filter_form(this, '%s','%s','%s','%s');"%(self.model._meta.app_label,
                                        self.model.__name__, self.fieldName(),ftitle),
                                'display': _(u'更多...')}

FilterSpec.register(lambda f: bool(f.rel), RelatedFilterSpec)

class ChoicesFilterSpec(FilterSpec):
        def __init__(self, f, request, params, model):
                super(ChoicesFilterSpec, self).__init__(f, request, params, model)
                self.lookup_kwarg = '%s__exact' % f.name
                self.lookup_val = request.GET.get(self.lookup_kwarg, None)

        def choices(self, cl):
                yield {'selected': self.lookup_val is None,
                           'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
                           'display': _(u'所有')}
                for k, v in self.field.choices:
                        yield {'selected': smart_unicode(k) == self.lookup_val,
                                        'query_string': cl.get_query_string({self.lookup_kwarg: k}),
                                        'display': v}

FilterSpec.register(lambda f: bool(f.choices), ChoicesFilterSpec)

class DateFieldFilterSpec(FilterSpec):
        def __init__(self, f, request, params, model):
                super(DateFieldFilterSpec, self).__init__(f, request, params, model)

                self.field_generic = '%s__' % self.field.name

                self.date_params = dict([(k, v) for k, v in params.items() if k.startswith(self.field_generic)])

                today = datetime.date.today()
                one_week_ago = today - datetime.timedelta(days=7)
                today_str = isinstance(self.field, models.DateTimeField) and today.strftime('%Y-%m-%d')
#                today_str = isinstance(self.field, models.DateTimeField) and today.strftime('%Y-%m-%d 23:59:59') or today.strftime('%Y-%m-%d')
                ftitle=smart_unicode(_(u"过滤器通过%(title)s")%{'title':self.field.verbose_name})
                self.links = (
                        (_(u'任何时候'), {}),
                        (_(u'今天'), {'%s__year' % self.field.name: str(today.year),
                                           '%s__month' % self.field.name: str(today.month),
                                           '%s__day' % self.field.name: str(today.day)}),
                        (_(u'前7天'), {'%s__gte' % self.field.name: one_week_ago.strftime('%Y-%m-%d'),
                                                         '%s__lte' % f.name: today_str}),
                        (_(u'本月'), {'%s__year' % self.field.name: str(today.year),
                                                         '%s__month' % f.name: str(today.month)}),
                        (_(u'今年'), {'%s__year' % self.field.name: str(today.year)}),
                        (_(u'指定范围...'), {'javascript': "$.zk._timerange_filter_form(this,'%s','%s');"%(self.field.name, ftitle)}),
                )

        def title(self):
                return self.field.verbose_name

        def choices(self, cl):
                for title, param_dict in self.links:
                        yield {'selected': self.date_params == param_dict,
                                   'query_string': param_dict.has_key('javascript') and ('javascript: '+param_dict['javascript']) or cl.get_query_string(param_dict, [self.field_generic]),
                                   'display': title}

FilterSpec.register(lambda f: isinstance(f, models.DateField), DateFieldFilterSpec)

class BooleanFieldFilterSpec(FilterSpec):
        def __init__(self, f, request, params, model):
                super(BooleanFieldFilterSpec, self).__init__(f, request, params, model)
                self.lookup_kwarg = '%s__exact' % f.name
                self.lookup_kwarg2 = '%s__isnull' % f.name
                self.lookup_val = request.GET.get(self.lookup_kwarg, None)
                self.lookup_val2 = request.GET.get(self.lookup_kwarg2, None)

        def title(self):
                return self.field.verbose_name

        def choices(self, cl):
                for k, v in ((_(u'所有'), None), (_(u'是'), '1'), (_(u'否'), '0')):
                        yield {'selected': self.lookup_val == v and not self.lookup_val2,
                                   'query_string': cl.get_query_string({self.lookup_kwarg: v}, [self.lookup_kwarg2]),
                                   'display': k}
                if isinstance(self.field, models.NullBooleanField):
                        yield {'selected': self.lookup_val2 == 'True',
                                   'query_string': cl.get_query_string({self.lookup_kwarg2: 'True'}, [self.lookup_kwarg]),
                                   'display': _(u'未知')}

FilterSpec.register(lambda f: isinstance(f, models.BooleanField) or isinstance(f, models.NullBooleanField), BooleanFieldFilterSpec)

# This should be registered last, because it's a last resort. For example,
# if a field is eligible to use the BooleanFieldFilterSpec, that'd be much
# more appropriate, and the AllValuesFilterSpec won't get used for it.
class AllValuesFilterSpec(FilterSpec):
        def __init__(self, f, request, params, model):
                super(AllValuesFilterSpec, self).__init__(f, request, params, model)
                self.lookup_val = request.GET.get(f.name, None)
                self.lookup_choices = model.objects.distinct().order_by(f.name).values(f.name)

        def title(self):
                return self.field.verbose_name

        def choices(self, cl):
                yield {'selected': self.lookup_val is None,
                           'query_string': cl.get_query_string({}, [self.field.name]),
                           'display': _(u'所有')}
                for val in self.lookup_choices:
                        val = smart_unicode(val[self.field.name])
                        yield {'selected': self.lookup_val == val,
                                   'query_string': cl.get_query_string({self.field.name: val}),
                                   'display': val}
FilterSpec.register(lambda f: True, AllValuesFilterSpec)
