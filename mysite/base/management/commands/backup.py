#!/usr/bin/env python
#coding=utf-8
import os
import time
import sys
import subprocess
import logging
import datetime
from django.conf import settings

logger = logging.getLogger()
hdlr = logging.FileHandler(settings.APP_HOME+"\\tmp\\backup.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.NOTSET)


def backupdb():
    from dbapp.models import DbBackupLog
    from base.options import Option
    from base.options import PersonalOption
    
    pos = PersonalOption.objects.filter(option__name="backup_sched")
    currenttime = datetime.datetime.now()
    fmt ="%Y-%m-%d %H:%M:%S"
    for i in pos:
        starttime,inc = i.value.split("|")
        starttime =datetime.datetime.strptime(starttime,fmt) 
        inc = int(inc)
        #dt_start =datetime.datetime.strptime(starttime,fmt)
        hl = DbBackupLog.objects.filter(user=i.user,imflag=False).order_by('-starttime')
        if hl.count()>0:
            ret = (hl[0].starttime - starttime).seconds*1.0/ (inc *60*60)
            if ret ==int(ret):
                dt_start = hl[0].starttime
            else:
                dt_start =starttime   
        else:
            dt_start =starttime
        k=1
        dd= datetime.datetime(currenttime.year,currenttime.month,currenttime.day,dt_start.hour,dt_start.minute,dt_start.second)
        if currenttime<dt_start:
            return
        while True:
#            dt_start_should = dt_start + datetime.timedelta(hours=  k * inc)
#            dt_start_from = dt_start_should - datetime.timedelta(seconds=60)
#            dt_start_to = dt_start_should + datetime.timedelta(seconds=60)
            dt_start_should =  dd +  datetime.timedelta(hours=  k * inc)
            dt_start_from =  dt_start_should - datetime.timedelta(seconds=60)
            dt_start_to = dt_start_should + datetime.timedelta(seconds=60)
            if currenttime<dt_start_from:
                break
            if currenttime>=dt_start_from and currenttime<=dt_start_to: 
                #print "starting  backup %s"%dt_start_should
                iCount=DbBackupLog.objects.filter(user=i.user,imflag=False,starttime__range=(dt_start_from,dt_start_to)).count()
                if not iCount:
                    ii=DbBackupLog(user=i.user,starttime= dt_start_should,imflag=False)
                    ii.save()
                break
            k+=1
    cunprocess=DbBackupLog.objects.filter(successflag='').order_by('starttime')
    if cunprocess:
        unprocess =cunprocess[0]
        backup_file=settings.APP_HOME+"\\tmp\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".json"
        try:
            p = subprocess.Popen("manage.pyc dumpdata >"+backup_file,shell=True,stderr=subprocess.PIPE)
            stderrdata = p.communicate()
            if p.returncode!=0:
                unprocess.successflag='2'
                unprocess.save()
                logger.error(stderrdata)
            elif p.returncode==0:
                unprocess.successflag='1'
                unprocess.save()
        except Exception,e:
            print e
