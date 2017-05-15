# -*- coding: utf-8 -*-
from mysite.base.sync_api import SYNC_MODEL
from mysite.base.cached_model import STATUS_OK, STATUS_INVALID, STATUS_LEAVE
from mysite.personnel.models.model_leave import get_leave_user_info
from mysite.base.sync_api import update_emp, update_emp_area, update_device
from mysite.base.sync_api import delete_emp, update_emp, delete_device


class save_hook(object):
    def __init__(self, is_new, obj, old_obj):
        self.obj = obj
        self.old_obj = old_obj
        self.is_new = is_new
        self.info_change = False
        self.emp_delete = False
        self.emp_recover = False
        self.from_dev = False
        self.card = None
        self.device_update = False
        self.area_change = False

    def check(self):
        if self.obj.__class__.__name__ == 'Employee':
            if hasattr(self.obj, 'from_dev') and getattr(self.obj, 'from_dev'):
                self.from_dev = True
                return self
            if self.is_new:
                #                if self.obj.isatt or self.obj.isatt=="":
                self.info_change = True
            else:
                tmp = self.old_obj
                obj = self.obj
                if tmp.status != obj.status and obj.status == 999:
                    self.emp_delete = True
                    return self
                #                if tmp.status!=obj.status and obj.status == 0 and self.obj.isatt:
                if tmp.status != obj.status and obj.status == 0:
                    self.emp_recover = True
                    return self
                #                if tmp and tmp.isatt!=obj.isatt:
                #                    if obj.isatt:
                #                        self.info_change = True
                #                    else:
                #                        self.emp_delete = True
                #                    return self
                #                self.info_change = tmp and  (tmp.Card!=obj.Card or  tmp.AccGroup!=obj.AccGroup or tmp.EName!=obj.EName or tmp.Privilege!=obj.Privilege or tmp.Password!=obj.Password) and self.obj.isatt
                self.info_change = tmp and (
                tmp.Card != obj.Card or tmp.AccGroup != obj.AccGroup or tmp.EName != obj.EName or tmp.Privilege != obj.Privilege or tmp.Password != obj.Password)
        elif self.obj.__class__.__name__ == 'IssueCard':
            if hasattr(self.obj, 'card_from_dev') and getattr(self.obj, 'card_from_dev'):
                return self
            elif self.obj.card_privage == '0':  # 非管理卡
                if not get_leave_user_info(self.obj.UserID, "isClassAtt"):  # 没有做关闭考勤操作
                    if self.obj.cardstatus in ['1', '4']:  # 更新卡号#'4'代表过期卡，目前考勤，门禁，没有过期卡概念，此处特殊处理一下
                        self.info_change = True
                        self.card = self.obj.cardno
                        self.obj = self.obj.UserID
                    else:
                        old = self.obj.UserID.Card
                        if old and str(old) == str(self.obj.cardno):  # 删除卡号
                            self.info_change = True
                            self.card = ''
                            self.obj = self.obj.UserID
        elif self.obj.__class__.__name__ == 'Device':
            if hasattr(self.obj, 'from_dev') and getattr(self.obj, 'from_dev'):
                self.from_dev = True
                return self
            else:
                self.device_update = True
        elif self.obj.__class__.__name__ == 'EmpChange':
            obj = self.obj
            if obj.changepostion == 4:
                self.area_change = obj.newids
        return self

    def sync(self):
        if self.obj.__class__.__name__ == 'Employee':
            if self.emp_delete:
                '''下发删除'''
                delete_hook(self.obj)
                return
            if self.info_change or self.emp_recover:
                '''下发信息更新(包含卡号更新)'''
                update_emp(self.obj, card=self.card)
            #            if  not self.from_dev and self.card==None and self.obj.isatt:#非卡号改变
            if not self.from_dev and self.card == None:  # 非卡号改变
                '''调整区域'''
                m_ids = [a.pk for a in self.obj.attarea.all()]
                update_emp_area(self.obj.PIN, m_ids)
        elif self.obj.__class__.__name__ == 'Device':
            if self.obj.device_type == 1 and self.device_update:
                update_device(self.obj)
        elif self.obj.__class__.__name__ == 'EmpChange':
            #            if self.area_change and self.obj.UserID.isatt:
            if self.area_change:
                m_ids = self.area_change
                update_emp_area(self.obj.UserID.PIN, m_ids)


def delete_hook(obj):
    if obj.__class__.__name__ == 'Employee':
        delete_emp(obj.PIN)
    elif obj.__class__.__name__ == 'Device':
        if obj.device_type == 1:
            delete_device(obj.sn)
    elif obj.__class__.__name__ == 'IssueCard':
        if obj.card_privage == '0':  # 非管理卡
            if obj.cardstatus == '1':  # 有效卡退卡
                update_emp(obj.UserID, card='')
            elif not get_leave_user_info(obj.UserID,
                                         "isClassAtt") and obj.cardstatus == '5':  # 没有做关闭考勤操作,关闭了消费，然后进行退卡操作的情况处理
                update_emp(obj.UserID, card='')

                # def area_hook(obj,old=None):
                #    if SYNC_MODEL:
                #        from sync_api import update_emp_area
                #        m_ids = [a.pk for a in obj.attarea.all()]
                #        update_emp_area(obj.PIN, m_ids)
                #        if old:
                #            old_dis = [a.pk for a in old.attarea.all()]
                #            if m_ids !=old_dis:
                #                update_emp_area(obj.PIN, m_ids)
                #        else:
                #            update_emp_area(obj.PIN, m_ids)
