#!/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime
import logging
import os
import subprocess

from mysite.base.dj6 import dict4ini
from django.conf import settings
from mysite.base.dbapp.models import DbBackupLog
from mysite.base.options import PersonalOption
from django.db import close_connection

logger = logging.getLogger()
hdlr = logging.FileHandler(settings.APP_HOME+"\\tmp\\backup.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.NOTSET)


def get_attsite_file():
    #current_path=os.path.split(__file__)[0]
    #if not current_path:
    current_path = settings.APP_HOME
    attsite=dict4ini.DictIni(current_path+"/attsite.ini")
    return attsite

def backupdb():

    close_connection()
    pos = PersonalOption.objects.filter(option__name="backup_sched")
    currenttime = datetime.datetime.now()
    fmt ="%Y-%m-%d %H:%M:%S"
    for i in pos:
        while True:
            #time.sleep(5)
            #currenttime = datetime.datetime.now()
            starttime, inc = i.value.split("|")
            starttime = datetime.datetime.strptime(starttime,fmt)#无论是否改变，重新获取
            dt = datetime.datetime(starttime.year,starttime.month,starttime.day)
            cur = datetime.datetime(currenttime.year,currenttime.month,currenttime.day)
            date_check = ((cur-dt).days*1.0)/int(inc)   #inc 单位：天
            #print '-----date_check=',date_check
            if date_check != int(date_check):
                break
            dt_start_should= datetime.datetime(currenttime.year,currenttime.month,currenttime.day,starttime.hour,starttime.minute,starttime.second)
            dt_start_from =  dt_start_should - datetime.timedelta(seconds=10)
            dt_start_to = dt_start_should + datetime.timedelta(seconds=180)

            #print '---currenttime=',currenttime
            #print '---dt_start_from=',dt_start_from
            if currenttime >= dt_start_from and currenttime <= dt_start_to:
                #print "starting  backup %s"%dt_start_should
                iCount=DbBackupLog.objects.filter(user=i.user,imflag=False,starttime__range=(dt_start_from,dt_start_to)).count()
                if not iCount:
                    ii=DbBackupLog(user=i.user,starttime= dt_start_should,imflag=False)
                    ii.save()
            break#不执行计划备份时，跳出while循环,继续for循环。防止立即备份不执行
    cunprocess = DbBackupLog.objects.filter(successflag='').order_by('starttime')
    #print '---cunprocess=',cunprocess
    if cunprocess:
        unprocess =cunprocess[0]
        database_user = settings.DATABASES["default"]["USER"]
        database_password = settings.DATABASES["default"]["PASSWORD"]
        database_engine = settings.DATABASES["default"]["ENGINE"]
        database_name = settings.DATABASES["default"]["NAME"]
        database_host = settings.DATABASES["default"]["HOST"]
        database_port = settings.DATABASES["default"]["PORT"]
        #backup_file=settings.APP_HOME+"\\tmp\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".json"

        try:
            backup_file = ""  
            dict = get_attsite_file()
            path = dict["Options"]["BACKUP_PATH"]#.encode('gbk')
            #print type(path)
            #print path
            if path == "":
                unprocess.successflag = '2'
                unprocess.save()
                return
            if not os.path.exists(path):
                os.mkdir(path)
            
            if database_engine == "django.db.backends.mysql":
                backup_file = path+"\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".sql"
            #backup_file = "python manage.pyc dumpdata >\"%s\""%backup_file
                if database_password != "":
                    backup_file = "mysqldump --hex-blob -l --opt -q -R --default-character-set=utf8 -h %s -u %s -p%s --port %s --database %s >%s"%(database_host, database_user, database_password, database_port, database_name, backup_file)
                else:
                    backup_file = "mysqldump --hex-blob -l --opt -q -R --default-character-set=utf8 -h %s -u %s --port %s --database %s >%s"%(database_host, database_user, database_port, database_name, backup_file)
            elif database_engine == "sqlserver_ado":
                database_name='[%s]'%database_name
                backup_file = path+"\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".bak"
                backup_file = '''sqlcmd -U %s -P %s -S %s -Q "backup database %s to disk='%s'"'''%(database_user,database_password,database_host,database_name,backup_file)
            elif database_engine == "django.db.backends.oracle":
                path = os.environ["path"]
                list = path.split(";")
                oracle_path = ""
                for i  in list:
                    if "oraclexe" in i:
                        oralce_path = i
                backup_file = path+"\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".dmp"
                backup_file = "%s\\exp %s/%s@%s file='%s'"%(oracle_path,database_user,database_password,database_name,backup_file)
            elif database_engine == "django.db.backends.postgresql_psycopg2":
                backup_file = path+"\\db_" + unprocess.starttime.strftime("%Y%m%d%H%M%S") +".bak"
                backup_file = 'pg_dump -h %s -c -p %s -U %s %s >%s'%(database_host,database_port,database_user,database_name,backup_file)
            p = subprocess.Popen(backup_file.encode('gbk'), shell=True, stderr=subprocess.PIPE)
            p.wait()
            stderrdata = p.communicate()
            if p.returncode != 0:
                unprocess.successflag = '2'
                unprocess.save()
                logger.error(stderrdata)
            elif p.returncode == 0:
                unprocess.successflag = '1'
                unprocess.save()
        except Exception as e:
            print(e)
