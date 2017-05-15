#coding=utf-8
from django.test import TestCase
from django.core.urlresolvers import reverse


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)
    def test_user_option(self):
        from views import user_option
        from base.options import options, SystemOption, PersonalOption
        resp=self.client.post(reverse(user_option), {
                        "email": "cc@cc.cc",
                        "first_name": "Chen",
                        "last_name": "Richard",
                        "base.datetime_format": "%Y/%m/%d %H:%M:%S",
                        "base.date_format": "%Y/%m/%d",
                        "base.language": "zh-cn",
                        "base.time_format": "%H:%M:%S",
                        "dbapp.theme": "flat",
                        "base.shortdate_format": "%y/%m/%d",
                        "base.defaul_app": "att",
                })
        #for o in PersonalOption.objects.all(): print "PersonalOption",o.option, o.value
        #for o in SystemOption.objects.all(): print "SystemOption", o.option, o.value
        self.failUnlessEqual(resp.status_code, 200)
        self.failUnlessEqual(options['base.language'], 'zh-cn')
        resp=self.client.post(reverse(user_option), {
                        "email": "cc@cc.cc",
                        "first_name": "Chen",
                        "last_name": "Richard",
                        "base.datetime_format": "%Y/%m/%d %H:%M:%S",
                        "base.date_format": "%Y/%m/%d",
                        "base.language": "_auto_",
                        "base.time_format": "%H:%M:%S",
                        "dbapp.theme": "3D",
                        "base.shortdate_format": "%y/%m/%d",
                        "base.defaul_app": "att",
                })
        #for o in PersonalOption.objects.all(): print "PersonalOption",o.option, o.value
        #for o in SystemOption.objects.all(): print "SystemOption", o.option, o.value
        self.failUnlessEqual(resp.status_code, 200)
        self.failUnlessEqual(options['dbapp.theme'], '3D')
        self.failUnlessEqual(options['base.language'], '_auto_')

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

