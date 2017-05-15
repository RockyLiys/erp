#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render_to_response

from mysite.base.cached_model import CachingModel

BOOLEANS = ((0, _(u"否")), (1, _(u"是")),)

FPVERSION = (
    ('9', _(u'9.0算法')),
    ('10', _(u'10.0算法')),
)

finger_idS = (
    (0, _(u'左手小指')),
    (1, _(u'左手无名指')),
    (2, _(u'左手中指')),
    (3, _(u'左手食指')),
    (4, _(u'左手拇指')),
    (5, _(u'右手拇指')),
    (6, _(u'右手食指')),
    (7, _(u'右手中指')),
    (8, _(u'右手无名指')),
    (9, _(u'右手小指')),
)


class OperatorTemplate(CachingModel):
    user = models.ForeignKey(User, verbose_name=_(u'指纹用户'))
    template1 = models.TextField(_(u'指纹模板'), null=True, editable=False)
    finger_id = models.SmallIntegerField(_(u'手指'), default=0, choices=finger_idS)
    valid = models.SmallIntegerField(_(u'是否有效'), default=1, choices=BOOLEANS)
    fpversion = models.CharField(verbose_name=_(u'指纹版本'), max_length=10, null=False, blank=False, editable=False,
                                 default='9', choices=FPVERSION)
    bio_type = models.SmallIntegerField(choices=((0, _(u"指纹")), (1, _(u'人脸'))), default=0)
    # SN = DeviceForeignKey(db_column='SN', verbose_name=_(u'登记设备'), null=True, blank=True)
    utime = models.DateTimeField(_(u'更新时间'), null=True, blank=True, editable=False)
    bitmap_picture = models.TextField(null=True, editable=False)
    bitmap_picture2 = models.TextField(null=True, editable=False)
    bitmap_picture3 = models.TextField(null=True, editable=False)
    bitmap_picture4 = models.TextField(null=True, editable=False)
    use_type = models.SmallIntegerField(null=True, editable=False)
    template2 = models.TextField(_(u'指纹模板'), null=True, editable=False)
    template3 = models.TextField(_(u'指纹模板'), null=True, editable=False)
    template_flag = models.BooleanField(_(u'指纹是否有效'), null=False, default=False, blank=True, editable=True)

    def __unicode__(self):
        return u"%s, %s" % (self.user, self.finger_id)

    def template(self):
        return self.OperatorTemplate.decode("base64")

    def temp(self):
        # 去掉BASE64编码的指纹模板中的回车
        return self.OperatorTemplate.replace("\n", "").replace("\r", "")

    class Admin(CachingModel.Admin):
        visible = False

    class Meta:
        app_label = 'base'
        db_table = 'base_operatortemplate'
        unique_together = (("user", "finger_id", "fpversion"),)
        verbose_name = _(u"用户指纹")
        verbose_name_plural = verbose_name
