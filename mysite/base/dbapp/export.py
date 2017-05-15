#coding=utf-8
from django.utils.encoding import smart_str
from django.shortcuts import render_to_response
from django.conf import settings
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.template import Template, Context
from django.http import QueryDict, HttpResponse, HttpResponseRedirect, HttpResponseNotModified

def openExportFmt(request):
        try:
                formats=file(settings.TEMPLATE_DIRS[0]+"/export_formats_"+request.LANGUAGE_CODE+".txt","r").readlines();
        except:
                formats=file(settings.TEMPLATE_DIRS[0]+"/export_formats.txt","r").readlines();
        return formats

def DataExport(request, dataModel, qs, format):
        template=""
        format, compress=(format+'_').split("_", 1)
        formats=openExportFmt(request);
        f=formats[int(format)-1] #employee_号码姓名对照表.txt:"{{ item.PIN.PIN }}", ...
        fds =f.split("_",1)+[""]
        if fds[0]==dataModel.__name__ and fds[1]:
                fds=fds[1].split(":",1)+[""]
                if fds[0] and fds[1]: # 号码姓名对照表.txt:"{{ item.PIN.PIN }}", ...
                                template=fds[1]
        fname, extname=fds[0].split(".")[-2:]
        if "_" in extname:
                extname, header=extname.split("_", 1)
        else:
                header=""
        if not template:  return render_to_response("info.html", {"title": _(u"导出数据"), "content": _(u"指定的数据格式不存在或不支持!")});
        if template[-1]=="\n": template=template[:-1]
        #print "template", template
        template=Template(template)
        content=[]
        if header: content=[header.decode("utf-8")]
        c=len(qs)
        for item in qs[:c>settings.MAX_EXPORT_COUNT and settings.MAX_EXPORT_COUNT or c]:
                content.append(template.render(Context({'item': item})))
        content=u"\r\n".join(content)
        response=HttpResponse()
        if "csv" in extname:
                response["Content-Type"]="text/csv; charset="+settings.NATIVE_ENCODE
        else:
                response["Content-Type"]="text/plain; charset="+settings.NATIVE_ENCODE
        response["Pragma"]="no-cache"
        response['Content-Disposition'] = u'attachment; filename='+(".".join([fname, extname]))
        response["Cache-Control"]="no-store"
        content=content.encode(settings.NATIVE_ENCODE)
        response["Content-Length"]=len(content);
        response.write(content);
        return response


