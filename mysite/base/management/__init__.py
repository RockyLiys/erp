#!/usr/bin/env python
# -*- coding:utf-8 -*-

from mysite.base.auth_model import CustomUser

def post_superuser_permissions():
    # 创建一个超级用户
    if not CustomUser.objects.filter(username="admin"):
        CustomUser.objects.create_superuser("admin", "liys_liys@163.com", "admin123")
