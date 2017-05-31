#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings


@login_required
def home(request):
    return render(request, 'base/home.html', locals())
