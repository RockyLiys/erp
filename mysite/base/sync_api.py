# -*- coding: utf-8 -*-

from mysite.base.ooredis import *
from mysite.base.crypt import decryption

import sys, os
import dict4ini
from django.conf import settings
from mysite.iclock.device_http.protocol_content import device_pin
from mysite.iclock.device_http.sync_action import set_area
from mysite.personnel.models import Employee as E
from mysite.iclock.device_http.sync_action import set_device
from mysite.iclock.models import Device as D
from mysite.iclock.device_http.sync_action import spread_employee
from mysite.iclock.device_http.protocol_content import device_pin
from mysite.iclock.device_http.sync_action import del_Employee, del_device, set_FingerPrint
from mysite.iclock.models.model_bio import Template
from mysite.iclock.models import FaceTemplate
from mysite.iclock.device_http.sync_action import set_Face
from mysite.iclock.device_http.sync_action import get_device_status, clean_cache_data, server_update_data, get_att_record,get_att_record_file, init_att_batch,get_count_cmd
from mysite.iclock.device_http.sync_action import del_FingerPrint
import os
import time
import subprocess
from mysite.base.ooredis.sync_redis import cleandb, safe_exit
from mysite.pos.pos_ic.ic_sync_model import Pos_Device
import datetime
from mysite.utils import get_option
from mysite.personnel.models import Employee
from mysite.base.ooredis.client import get_client
from mysite.utils import get_option
from mysite.iclock.device_http.sync_action import clean_attpic, clean_att, clean_data, reboot_device, get_info, collect_device_employee, collect_device_att, collect_device_data, spread_device_employee
from mysite.iclock.device_http.sync_action import del_Face, get_FingerPrint_count, get_face_count
from mysite.iclock.device_http.protocol_content import device_pin


def update_emp(emp,card=None,call_sync=True):
    '''
    更新人员info数据
    '''
    m_dict = {}
    m_dict["AccGroup"] = emp.AccGroup
    m_dict["EName"] = emp.EName
    m_dict["Card"] = card and card or emp.Card
    m_dict["Privilege"] = emp.Privilege
    m_dict["TimeZones"] = emp.TimeZones
    try:
        m_dict["Password"] = emp.Password and decryption(emp.Password) or ''
    except:
        print(emp.Password)
        import traceback;traceback.print_exc()
        m_dict["Password"] = ''
    # msg = set_info(device_pin(emp.PIN),m_dict,call_sync)
#    if msg:
#        raise Exception(msg)

def update_emp_area(pin, ids, call_sync=True):
    '''
    更新人员区域
    '''
    pin = device_pin(pin)
    msg = set_area(pin,ids,call_sync)
#    if msg:
#        raise Exception(msg)

def init_emp_data(area0=False):
    objs = E.objects.all()
    for e in objs:
        update_emp(e,call_sync=False)
        ids = [a.pk for a in e.attarea.all()]
        if area0:ids=[]
        update_emp_area(e.PIN,ids,call_sync=False)
        
def init_device_data():
    objs = D.objects.filter(device_type__exact=1)
    for e in objs:
        update_device(e)
    
def update_device(device):
    '''
    更新设备信息
    '''
    m_dict = {}
    m_dict["ipaddress"] = device.ipaddress
    m_dict["alias"] = device.alias
    m_dict["area"] = device.area.pk
    m_dict["push_status"] = device.push_status
    m_dict["log_stamp"] = device.log_stamp
    m_dict["oplog_stamp"] = device.oplog_stamp
    m_dict["photo_stamp"] = device.photo_stamp
    m_dict["trans_times"] = device.trans_times
    m_dict["trans_interval"] = device.trans_interval
    m_dict["tz_adj"] = device.tz_adj
    m_dict["update_db"] = device.update_db
    msg = set_device(device.sn,m_dict)
    
def spread_emp(e):
    '''
    重新分发人员数据(基本信息、指纹、面部)
    '''
#    from mysite.personnel.models import Employee
#    obj = Employee.objects.filter(PIN=pin)
#    if len(obj)>0:
#        update_emp(obj[0])
    update_emp(e,call_sync=False)
    ids = [a.pk for a in e.attarea.all()]
    update_emp_area(e.PIN,ids,call_sync=False)
    
    pin = device_pin(e.PIN)
    msg = spread_employee(pin)
#    if msg:
#        raise Exception(msg)


def delete_emp(pin):
    '''
    删除人员
    '''
    pin = device_pin(pin)

    msg = del_Employee(pin)
#    if msg:
#        raise Exception(msg)

def delete_device(sn):
    '''
    删除设备
    '''
    msg = del_device(sn)

def update_emp_fp(pin,fpversion,fid,data,call_sync=True,force=False):
    '''
    更新人员指纹
    '''

    pin = device_pin(pin)
    msg = set_FingerPrint(pin,fpversion,fid,data,call_sync,force)
#    if msg:
#        raise Exception(msg)

def init_fp_data():
    objs = Template.objects.all()
    for e in objs:
        update_emp_fp(e.UserID, e.Fpversion, e.FingerID,None,call_sync=False)

def init_face_data():

    objs = FaceTemplate.objects.all()
    for e in objs:
        set_Face(device_pin(e.user), e.face_ver, e.faceid,None,call_sync=False)
        
def update_emp_pic(pin, data,call_sync=True):
    '''
    更新人员指纹
    '''
    from mysite.iclock.device_http.protocol_content import device_pin
    pin = device_pin(pin)
    from mysite.iclock.device_http.sync_action import set_EmployeePic
    msg = set_EmployeePic(pin,data,call_sync)
#    if msg:
#        raise Exception(msg)

def init_pic_data():

    objs = Employee.objects.exclude(photo='')
    for e in objs:
        update_emp_pic(e.PIN, None,call_sync=False)

def get_pos_site_file():

    current_path = settings.WORK_PATH
    pos_config=dict4ini.DictIni(current_path+"/pos/pos_config.ini")
    return pos_config

#保持redis中消费设备的数据到pos_config.ini文件
def set_pos_site_file():

    if get_option("POS_IC"):
        r_client = get_client()
        all_pos_device = r_client.keys("pos_device:*:data")
        for i in all_pos_device:
            sn = i.split(":")[1]
            pos_log_stamp_id = Dict(i)['pos_log_stamp_id']
            full_log_stamp_id = Dict(i)['full_log_stamp_id']
            allow_log_stamp_id = Dict(i)['allow_log_stamp_id']
            pos_log_bak_stamp_id = Dict(i)['pos_log_bak_stamp_id']
            full_log_bak_stamp_id = Dict(i)['full_log_bak_stamp_id']
            allow_log_bak_stamp_id = Dict(i)['allow_log_bak_stamp_id']
            pos_config = get_pos_site_file()
            redis_key = "pos_device:%s:data"%sn
            redis_value = pos_log_stamp_id +"%"+full_log_stamp_id+"%"+allow_log_stamp_id+"%"+pos_log_bak_stamp_id+"%"+full_log_bak_stamp_id+"%"+allow_log_bak_stamp_id
            pos_config["Pos_Device"][redis_key]=redis_value
            pos_config.save()
            
#获取pos_config.ini文件中的数据保持到redis
def update_redis_pos_device():

    if get_option("POS_IC"):
        pos_config = get_pos_site_file()
        
        pos_device_list = {}
        pos_device_list  = pos_config["Pos_Device"]
        for i in pos_device_list.items():
            sn = i[0].split(":")[1]
            pos_log_stamp_id = i[1].split("%")[0]
            full_log_stamp_id = i[1].split("%")[1]
            allow_log_stamp_id = i[1].split("%")[2]
            pos_log_bak_stamp_id = i[1].split("%")[3]
            full_log_bak_stamp_id = i[1].split("%")[4]
            allow_log_bak_stamp_id = i[1].split("%")[5]
            
            m_dict = {}
            m_dict["sn"] = sn
            m_dict["pos_log_stamp_id"] = pos_log_stamp_id or 0
            m_dict["full_log_stamp_id"] = full_log_stamp_id or 0
            m_dict["allow_log_stamp_id"] = allow_log_stamp_id or 0

            m_dict["pos_log_bak_stamp_id"] = pos_log_bak_stamp_id or 0 
            m_dict["full_log_bak_stamp_id"] = full_log_bak_stamp_id or 0
            m_dict["allow_log_bak_stamp_id"] = allow_log_bak_stamp_id or 0
            m_dict["pos_dev_data_status"] = True
            
            m_dict["pos_all_log_stamp"] = 0
            m_dict["pos_log_stamp"] = 0
            m_dict["full_log_stamp"] = 0 
            m_dict["allow_log_stamp"] = 0 
            m_dict["last_activity"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            r_device=Pos_Device(sn)
            r_device.sets(m_dict)


    
def reset_data():

    dev_sv = device_service()
    dev_sv.suspend()
    print('Initting environment')
    try:
        cur_path = os.getcwd()
        os.chdir('../../python-support/redis/redis-2.0.2')
        p = subprocess.Popen('cmd.exe /c redis-server.exe redis.conf',shell=False)
        os.chdir(cur_path)
    except:
        import traceback;traceback.print_exc()
        print('Redis start error')
        return 
    print('Save pos device for ini...')
    set_pos_site_file()
    print('Clean redis data ')
    time.sleep(3)
    cleandb()
    print('Initting employee data...')
    init_emp_data()
    print('Initting device data...')
    init_device_data()
    print('Initting finger data...')
    init_fp_data()
    print('Initting face data...')
    init_face_data()
    print('Initting pos device data...')
    update_redis_pos_device()
    if EN_EMP_PIC:
        print('Initting  empic data...')
        init_pic_data()
    print('Reducing environment')
    
    
    safe_exit()
    dev_sv.recover()
    print("Completed.")
    
def delete_emp_fp(pin):
    '''
    删除人员指纹
    '''
    pin = device_pin(pin)

    msg = del_FingerPrint(pin)
#    if msg:
#        raise Exception(msg)
    
def delete_emp_fc(pin):
    '''
    删除人员面部
    '''
    pin = device_pin(pin)

    msg = del_Face(pin)
#    if msg:
#        raise Exception(msg)
    

def do_clean_attpic(sn):
    sn = str(sn)
    msg = clean_attpic(sn)
    if msg:
        raise Exception(msg)
    
def do_clean_att(sn):
    sn = str(sn)
    msg = clean_att(sn)
    if msg:
        raise Exception(msg)
    
def do_clean_data(sn):
    sn = str(sn)
    msg = clean_data(sn)
    if msg:
        raise Exception(msg)
    
def do_reboot_device(sn):
    sn = str(sn)
    msg = reboot_device(sn)
    if msg:
        raise Exception(msg)
    
def do_get_info(sn):
    sn = str(sn)
    msg = get_info(sn)
    if msg:
        raise Exception(msg)
def do_collect_device_employee(sn):
    '''
    重新收集人员 (基本信息和指纹)
    '''
    sn = str(sn)
    msg = collect_device_employee(sn)
    if msg:
        raise Exception(msg)
    
def do_collect_device_att(sn):
    '''
    重新收集考勤记录
    '''
    sn = str(sn)
    msg = collect_device_att(sn)
    if msg:
        raise Exception(msg)
    
def do_collect_device_data(sn):
    '''
    重新收集数据
    '''
    sn = str(sn)
    msg = collect_device_data(sn)
    if msg:
        raise Exception(msg)
    
def do_spread_device_employee(obj):
    '''
    重新分发人员 (基本信息和指纹)
    '''
    update_device(obj)
    sn = str(obj.sn)
    msg = spread_device_employee(sn)
    if msg:
        raise Exception(msg)
    
class device_service(object):
    zkeco_c = 0
    att_c = 0
    
    def suspend(self):
        from django.core.cache import cache
        self.zkeco_c = cache.get("ZKECO_DEVICE_LIMIT")
        self.att_c = cache.get("ATT_DEVICE_LIMIT")
        cache.set("ZKECO_DEVICE_LIMIT",0 ,2592000)
        cache.set("ATT_DEVICE_LIMIT",0 ,2592000)
    
    def recover(self):
        from django.core.cache import cache
        cache.set("ZKECO_DEVICE_LIMIT",self.zkeco_c,2592000)
        cache.set("ATT_DEVICE_LIMIT",self.att_c ,2592000)
     

def get_emp_fp_count(pin):
    pin = device_pin(pin)
    return get_FingerPrint_count(pin)

def get_emp_face_count(pin):
    pin = device_pin(pin)
    return get_face_count(pin)
