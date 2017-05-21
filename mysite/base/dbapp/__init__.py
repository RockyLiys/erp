# -*- coding: utf-8 -*-
from mysite import base
# from django.template import add_to_builtins
# add_to_builtins('dbapp.templatetags.dbapp_tags')
# add_to_builtins('base.templatetags.base_tags')

from django.contrib.auth.models import User
# from dbapp.models import DbBackupLog
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
from django.conf import settings
template_display = False#默认不显示User的指纹数
try:
    template_display = not settings.ZKACCESS_5TO4 #4.1不显示   
except:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
    from django.conf import settings
    try:
        template_display = not settings.ZKACCESS_5TO4
    except:
        pass

# if template_display:#
#     User.Admin.list_display=('username', 'first_name', 'last_name','groups|detail_str','email', 'is_staff|boolean_icon','is_superuser|boolean_icon','date_joined|fmt_shortdatetime','last_login|fmt_shortdatetime','get_user_template')
# else:#4.1
#     User.Admin.list_display=('username', 'first_name', 'last_name','groups|detail_str','email', 'is_staff|boolean_icon','is_superuser|boolean_icon','date_joined|fmt_shortdatetime','last_login|fmt_shortdatetime')
#