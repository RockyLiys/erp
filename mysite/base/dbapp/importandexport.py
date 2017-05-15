#coding=utf-8
from django.utils.translation import ugettext_lazy as _
from base.middleware import threadlocals
from django.http import HttpResponse,HttpResponseRedirect
from modelutils import GetModel
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson   
from django.template import Template,Context,loader,RequestContext,TemplateDoesNotExist
from utils import getJSResponse
from django.utils.encoding import smart_str
from datetime import datetime
from dbapp.enquiry import Enquiry
from django.shortcuts import render_to_response
from django.db.models import ForeignKey
import xlrd
import sys
import codecs
from django.db.models import Q
from base.log import logger
from django.template.loader import render_to_string
from django.conf import settings
import threading
from django.core.cache import cache



#uploadpath="c:\\upload\\"
uploadpath=settings.ADDITION_FILE_ROOT+"/"
filecoding={
    #'gb18030':_(u"简体"),
    #'big5':_(u"繁体"),
    'utf-8':_("UTF-8"),
}

#定义  进度条 字典
processdata = {
    'index':1,
    'total':1,
    'process':0,
    'return_value':"",
}
#定义进度条
user_process={}
#存放导入数据
IMPORT_DATA = []
#缓存的键值
SESSION_PRO_KEY = ""


#分线程处理
class TThreadComm(object):
    def __init__(self,func,args):
        self.func = func
        self.args = args

    def __call__(self):
        apply(self.func, self.args)

def show_import(request,app_label,model_name):
    from modelutils import GetModel
    #tables={'Employee':_(u'人员表'),'department':_(u'部门表')}
    model=GetModel(app_label,model_name)
    tables={model._meta.module_name:model._meta.verbose_name}
    #tables[model_name]=model_name;
    #t=loader.get_template("import.html")
    #return HttpResponse(t.render(RequestContext(request,{
   #                    'tables':tables
   #                    }))
    from django.utils.translation.trans_real import get_language_from_request
    lang_code=get_language_from_request(request)
    if model_name =='EmpSpecDay':
        return render_to_response('simple_import.html', {'tables': tables,"lang_code":lang_code})
    else:
        return render_to_response('import.html', {'tables': tables,"lang_code":lang_code})

def show_simple_import(request,app_label,model_name):
    from modelutils import GetModel

    model=GetModel(app_label,model_name)
    tables={model._meta.module_name:model._meta.verbose_name}

    from django.utils.translation.trans_real import get_language_from_request
    lang_code=get_language_from_request(request)
    return render_to_response('simple_import.html', {'tables': tables,"lang_code":lang_code})

    
    
def get_importPara(request):
    
    ########################## 导入参数的获取和设置 ########################   
    tablename=""            #导入表名
    filetype=""             #文件类型   txt   xls   csv
    sparator=0              #分隔号    0智能查找    1 制表符    2   按分隔符 
    sparatorvalue=""        #分隔符
    headerflg=1             #文件内容是否含有标题
    headerln=1              #标题在文件中的行号
    recordln=2              #记录从第几行起
    filename=""             #保存上传文件的文件名
    tablename=""            #表名
    autosplit=[",",";",":","\t"," "]    #智能查找分隔符
    unicode_=""                  #字符编号
    file_obj=""
    fields=[]
    fieldsdesc=[]
    try:
        #获取导入参数
        data=dict(request.POST)
        filetype=str(data["filetype"][0])
        sparator=int(data["sparator"][0])
        sparatorvalue=data["sparatorvalue"][0]
        headerflg=int(data["header"][0])
        headerln=int(data["headerln"][0])
        recordln=int(data["recordln"][0])
        unicode_=str(data["selectunicode"][0])
        tablename=str("".join(data["tablename"][0].split()))
        
        #表字段及描述文字
        index_fields=[]
        model,flds,rlfield=findAllFieldsAndModel(tablename,index_fields)
        for f in index_fields:
            fields.append(f)
            fieldsdesc.append(flds[f])    
        if index_fields:
            fields=index_fields
        #获取文件           
        file_obj = request.FILES.get('file', None)
    except:
        import traceback; traceback.print_exc()
        return HttpResponse(u"%s"%_(u"取文件参数错误"))
    ########################## 获取文件数据 ########################       
    if file_obj:        
        # 取得文件名

        
        
        op=threadlocals.get_current_user()        
        dtstr=""
        dt=datetime.now()        
        dtstr=str(dt.year)+str(dt.month)+str(dt.day)+str(dt.hour)+str(dt.minute)+str(dt.second)        
        filename=op.username+dtstr+"."+filetype
        sheet_data = []
        if filetype=='txt' or filetype=='csv':
            try:
                fs = file_obj.file
                rec=fs.readline()
                while rec!="":
                    rec=rec.decode(unicode_)
                    if rec.endswith("\r\n"):
                        rec=rec[:len(rec)-2]   
                    if int(sparator)==0:
                        for sp in autosplit:
                            if len(rec.split(sp))> 1:                        
                                sparatorvalue=sp            
                    linedata=rec.split(sparatorvalue)
                    ltmp=[]
                    for l in linedata:
                        if l.startswith('"') and l.endswith('"'):
                            ltmp.append(['3',u"%s"%l[1:len(l)-1]])
                        else:
                            ltmp.append(['3',u"%s"%l])
                    sheet_data.append(ltmp)
                    rec=fs.readline()
            except:
                import traceback; traceback.print_exc()
                return HttpResponse(u"%s"%_(u"处理上传的文件错误!"))
            
        elif filetype=='xls':
            try:
                tmp_file_path = uploadpath+filename              
                wr=file(tmp_file_path,"w+b",)
                linedata=file_obj.file.read()
                wr.write(linedata)
                wr.close()
                ds=ParseXlsUxlrd(tmp_file_path)    
                for sh in range(len(ds)):
                    if len(ds[sh][1])>=0:
                        sheet_data=ds[sh][1]                        
                        break
                import os
                os.remove(tmp_file_path)
            except:
                import traceback; traceback.print_exc()
                return HttpResponse(u"%s"%_(u"处理XLS文件错误!"))         
        else:            
            return HttpResponse(u"%s"%_(u"上传文件类型未知!"))
        ########################## 返回相关数据 ########################
        if  sheet_data:
                import pickle
                pic_s = pickle.dumps(sheet_data)
                wr=file(uploadpath+filename,"w",)
                wr.write(pic_s)
                wr.close()
                session_key=request.session.session_key+"importfile"
                global IMPORT_DATA
#                if  IMPORT_DATA:    
#                    return HttpResponse(u"%s"%_(u"有其他用户在导入！"))
#                else:
                IMPORT_DATA=sheet_data                
#                cache.set(session_key,sheet_data,7200)#把文件存放到缓存中
                global SESSION_PRO_KEY
                SESSION_PRO_KEY = request.session.session_key+"process"
                processdata={}
                processdata["process"]=0
                processdata["index"]=1
                processdata["return_value"]=""
                processdata["total"]=1
                cache.set(SESSION_PRO_KEY,processdata,3600)
                
                hdata=[]
                ddata=[]
                if headerflg and headerln:
                    if (len(sheet_data)>=headerln):
                        hdata = [ e[1] for e in sheet_data[ headerln-1]]
                if len(sheet_data)>=recordln:
                    ddata =[ e[1] for e in  sheet_data[recordln-1]  ]         
                ret={}
                ret['tablename']=tablename
                ret['headdata']=hdata
                ret['recorddata']=ddata
                ret['fields']=fields
                ret['fieldsdesc']=fieldsdesc
                ret['filetype']=filetype
                ret['filename']=filename
                ret['sparatorvalue']=sparatorvalue
                ret['headln']=headerln
                ret['recordln']=recordln
                ret['unicode']=unicode_
                ret=simplejson.dumps(ret)                
                return HttpResponse(u"%s"%ret)
        else:
            return HttpResponse(u"%s"%_(u"文件内容为空!"))
    
def simple_get_importPara(request):
    try:
        #获取导入参数
        data=dict(request.POST)
        #print data
        filetype=str(data["filetype"][0])
        #获取文件
        file_obj = request.FILES.get('file', None)
    except:
        import traceback; traceback.print_exc()
        return HttpResponse(u"%s"%_(u"取文件参数错误"))
    if filetype == 'xls': 
        if file_obj:        
            op=threadlocals.get_current_user()        
            dtstr=""
            dt=datetime.now()        
            dtstr=str(dt.year)+str(dt.month)+str(dt.day)+str(dt.hour)+str(dt.minute)+str(dt.second)        
            filename=op.username+dtstr+"."+filetype
        try:
            print "Process xls file.........."
            stw=file_obj.file
            
            filedata=[]
            wr=file(uploadpath+filename,"w+b",)
            linedata=stw.read()
            wr.write(linedata)
            wr.close()
            
            ret={}
            ret['filename']=filename
            ret=simplejson.dumps(ret)              
            return HttpResponse(u"%s"%ret)
        except:
            import traceback; traceback.print_exc()
            return HttpResponse(u"%s"%_(u"处理XLS文件错误!"))
    else:
        return HttpResponse(u"%s"%_(u"上传文件类型未知!"))

def file_simple_import(request,app_label,model_name):
    
    data=dict(request.POST)
    filename=data["txtfilename"][0]           
    filepath = uploadpath+filename
    mymodel=GetModel(app_label,model_name)
    
    sheetdata=ParseXlsUxlrd(filepath)
    datash=sheetdata[0][1]  
    
    fail_list=[]
    for row in range(len(datash)):  
        if row==0:
            continue
        obj = mymodel()
        ipt_data = row+1
        ept = obj.do_import(datash[row])
        if isinstance(ept,Exception):
            fail_list.append({'data':ipt_data,'error':ept.message})
    if fail_list:
        output = ""
        for e in fail_list:
            output += (u"第%s行"%(e['data'])+u" : %s \n"%(e['error']) )
        return HttpResponse(u"%s"%_(u"处理以下行出错\n")+"%s"%output)
    else:
        return HttpResponse(u"%s"%_(u"文件导入操作完成！"))

    

    
def file_import(request):                   #文件导入处理
#    filename=""
#    filetype=""
#    tablename=""
#    sparatorvalue=","
#    fields={}               #已选择字段列表
#    target=[]               #目标文件列号
#    errmode=1               #出错处理方式     1  跳过错误 继续处理     2  退出，并删除已导入记录
#    headln=1
#    recordln=2
#    unicode_="utf-8"
#    relatefield=[]
#    relrecs=[]
#    addrelate=1             #关联记录处理  1   自动增加       2  关键记录不存在，跳过当次记录,不增加关联记录
    
    data=dict(request.POST)
#    errmode=int(data["errmode"][0])
#    filename=data["txtfilename"][0]
#    filetype=data["txtfiletype"][0]
#    sparatorvalue=data["sparatorvalue"][0]
#    headln=int(data["headln"][0])
#    recordln=int(data["recordln"][0])
#    tablename=data["txttablename"][0]
#    unicode_=data["unicode"][0].decode()
#    addrelate=int(data["addrelate"][0])
    session_key=request.session.session_key
    #查找字段列表，目标列号
#    for n,v in data.items():
#        if n.startswith("_chk_"):
#            
#            field=str(data["_select_"+ n[5:]][0]).decode(unicode_)
#            fields[field]=int(n[5:])
#    #查找模型
#    model,flds,rlfield=findAllFieldsAndModel(tablename)
#
#    objlist=[]
#    Employee=GetModel("personnel","Employee")
#    Department=GetModel("personnel","Department")
#    error_list=[]
    
    t = threading.Thread(target = TThreadComm(writefile, (data,session_key)))
    t.start()
        
    return HttpResponse(u"%s"%_(u"开始导入"))

def writefile(data,session_key):
    '''
    新的读写文件
    '''
    filename=""
    filetype=""
    tablename=""
    sparatorvalue=","
    fields={}               #已选择字段列表
    target=[]               #目标文件列号
    errmode=1               #出错处理方式     1  跳过错误 继续处理     2  退出，并删除已导入记录
    headln=1
    recordln=2
    unicode_="utf-8"
    relatefield=[]
    relrecs=[]
    addrelate=1             #关联记录处理  1   自动增加       2  关键记录不存在，跳过当次记录,不增加关联记录
    
#    data=dict(request.POST)
    #print data
    errmode=int(data["errmode"][0])
    filename=data["txtfilename"][0]
    filetype=data["txtfiletype"][0]
    sparatorvalue=data["sparatorvalue"][0]
    headln=int(data["headln"][0])
    recordln=int(data["recordln"][0])
    tablename=data["txttablename"][0]
    unicode_=data["unicode"][0].decode()
    addrelate=int(data["addrelate"][0])
#    session_key=request.session.session_key
    
    savefilekey = session_key+ "importfile"
    global SESSION_PRO_KEY
    if SESSION_PRO_KEY:
        session_key = SESSION_PRO_KEY
    else:
        session_key = str(session_key)+"process"
    #查找字段列表，目标列号
    for n,v in data.items():
        if n.startswith("_chk_"):
            
            field=str(data["_select_"+ n[5:]][0]).decode(unicode_)
            fields[field]=int(n[5:])
    #查找模型
    model,flds,rlfield=findAllFieldsAndModel(tablename)
    objlist=[]
    Employee=GetModel("personnel","Employee")
    Department=GetModel("personnel","Department")
    error_list=[]
    
    
    #加入缓存
    processdata={}
    processdata["process"]=0
    processdata["index"]=1
    processdata["return_value"]=""
    processdata["total"]=1
    cache.set(session_key,processdata,3600)
   
    
    
    try:
#        if filetype=="txt" or filetype=="csv":#处理 txt与csv
#           pass 
#           
#        elif filetype == "xls" : # word 2007 xls文件后缀应该添加
#            sheetdata=ParseXlsUxlrd(uploadpath+filename)
#        datash=cache.get(savefilekey)
        #在运行开始让进度条 初始化为 0
        
        #global IMPORT_DATA
        import pickle
        f=file(uploadpath+filename)
        datash=pickle.load(f)
        f.close()
        import os
        os.remove(uploadpath+filename)
        IMPORT_DATA=[]
        processdata['total'] = len(datash)#文件总数
        cache.set(session_key,processdata,3600)
        deptfkey={}#存放有外键的 字典
        hasdeptf=False
        perfkey={}# 模型 字段 的存放的点  子段  在列表的位置 对应关系
        #这里暂时只是考虑 人员与部门
        for fld,value in fields.items():#遍历提交 对应关系
            if fld.find(".")>0:
                fr=fld.split(".")
                if fr[0]=="Department":
                    deptfkey[fr[1]]=value
            else:
                perfkey[fld]=value                    
        if deptfkey.has_key("code"):
            hasdeptf=True
                    
        for row in range(len(datash)):#每行每行开始读取
            if row==len(datash):
                processdata["process"]=processdata["total"]
            else:
                processdata["process"] = processdata["process"]+1
            cache.set(session_key,processdata,3600)
            try:
                if row>=recordln-1:#从第二行开始读取数据 
                    isSave=True #这里定义几个标识符 
                    has_property=False
                    strwhere={}
                    upobj=""
                    if model == Employee:
                        default_deptcode=1
                        if hasdeptf:
                            de_code=datash[row][deptfkey["code"]][1]
                            if type(de_code) == float:
                                de_code=str(int(de_code))
                            de_name=de_code
                            if deptfkey["name"]:
                                de_name=datash[row][deptfkey["name"]][1]
                                if type(de_name)==float:
                                    de_name=str(int(de_name))
                                
                            tem=Department.objects.filter(code__exact=de_code)
                            if  len(tem) > 0 :
                                pass
                            else:
                                Department(code=de_code,name=de_name).save()
                            default_deptcode=Department.objects.filter(code__exact=de_code)[0].id
                        model_emp=sys.modules['mysite.personnel.models.model_emp']
                        format_pin=getattr(model_emp,"format_pin")
                        
                        update=False
                        for per_fileds in perfkey:
                            if per_fileds=="PIN":
                                try:
                                    tt=Employee.all_objects.get(PIN=format_pin(datash[row][perfkey[per_fileds]][1]))
                                    update=True
                                    break;
                                except:
                                    pass
                        if not update:                            
                            tt=Employee()
                        for per_fileds in perfkey:
                            if per_fileds == "Gender":#性别 特殊处理
                                sex = datash[row][perfkey[per_fileds]][1]
                                if  not sex:
                                    tt.__setattr__(per_fileds,"")
                                else:
                                    if sex  in ["Male",u"男","M"]:
                                        tt.__setattr__(per_fileds,"M")
                                    elif sex in ["Female",u"女","F"]:
                                        tt.__setattr__(per_fileds,"F")
#                                    else:
#                                        tt.__setattr__(per_fileds,"")
                            elif per_fileds=="PIN" and update:
                                continue        
                            else:
                                if datash[row][perfkey[per_fileds]][0]==2:
                                    tvalue=str(int(datash[row][perfkey[per_fileds]][1]))
                                else:
                                    tvalue=datash[row][perfkey[per_fileds]][1]
                                tt.__setattr__(per_fileds,tvalue)
                            
                        tt.DeptID_id=default_deptcode
                        tt.save()
                        tt.__setattr__('attarea',(1,))#默认区域
                        tt.save()
                    elif model == Department:#如果导入是部门的话
                        super_departid=None
                        try:
                            if deptfkey.has_key("code"):
                                de_code=datash[row][deptfkey["code"]][1]
                                if type(de_code) == float:
                                     de_code=str(int(de_code))
                                super_departid=Department.objects.filter(code__exact=de_code)[0].id
                                
                            elif deptfkey["name"]:
                                de_name=datash[row][deptfkey["name"]][1]
                                if type(de_name) == float :
                                    de_name=str(int(de_name))
                                
                                super_departid=Department.objects.filter(name__exact=de_name)[0].id
                        except:
                            super_departid=None
                            pass
                        
                        tt = Department()#开始 往 部门表中插入数据
                        for per_fileds in perfkey:
                            tt.__setattr__(per_fileds,datash[row][perfkey[per_fileds]][1])
                        if  super_departid:
                            tt.parent_id = super_departid
                        tt.save()
            except Exception,e:
               #logger.error("%s"%e)
               try:
                   error_list.append(str(row+1)+u"%s"%_(u" 行      ")+u"%s"%e)
               except:
                   error_list.append(str(row+1))
                   pass
               if errmode==1:                      # 按错误处理方式处理数据
                   continue                        
               else:
                   raise
                
        if error_list:
            if len(error_list)>10:
                processdata["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list[:10]))+u"%s"%_(u"\n...\n还有%s条未显示，其它行导入操作成功！")%(len(error_list)-10))
            else:
                processdata["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list))+u"%s"%_(u"\n出错，其它行导入操作成功！"))
        else:
             processdata["return_value"]=(u"%s"%_(u"文件导入操作完成！"))
        cache.set(session_key,processdata,3600)
        
                                               
    except Exception, e:
        logger.error("%s"%e)
        if errmode==2:                  # 按错误处理方式处理数据
            j=0
            while j<len(objlist):                  #删除已保存记录
                objlist[j].delete()
            for ro in relrecs:          #删除关联表记录
                ro.delete()
        processdata["return_value"]=(u"%s"%_(u"文件导入出错!"))
        cache.set(session_key,processdata,3600)
        


#增加线程处理 数据导入 相关事宜
def detailthread(data,session_key):
    filename=""
    filetype=""
    tablename=""
    sparatorvalue=","
    fields={}               #已选择字段列表
    target=[]               #目标文件列号
    errmode=1               #出错处理方式     1  跳过错误 继续处理     2  退出，并删除已导入记录
    headln=1
    recordln=2
    unicode_="utf-8"
    relatefield=[]
    relrecs=[]
    addrelate=1             #关联记录处理  1   自动增加       2  关键记录不存在，跳过当次记录,不增加关联记录
    
#    data=dict(request.POST)
    #print data
    errmode=int(data["errmode"][0])
    filename=data["txtfilename"][0]
    filetype=data["txtfiletype"][0]
    sparatorvalue=data["sparatorvalue"][0]
    headln=int(data["headln"][0])
    recordln=int(data["recordln"][0])
    tablename=data["txttablename"][0]
    unicode_=data["unicode"][0].decode()
    addrelate=int(data["addrelate"][0])
#    session_key=request.session.session_key
    
    session_key = str(session_key)
    #查找字段列表，目标列号
    for n,v in data.items():
        if n.startswith("_chk_"):
            
            field=str(data["_select_"+ n[5:]][0]).decode(unicode_)
            fields[field]=int(n[5:])
    #查找模型
    model,flds,rlfield=findAllFieldsAndModel(tablename)

    objlist=[]
    Employee=GetModel("personnel","Employee")
    Department=GetModel("personnel","Department")
    error_list=[]
    
#    global user_process
#    #加入全局变量
#    processdata_global={}
#    
#    user_process[session_key]=processdata_global
#    user_process[session_key]["process"]=0
#    user_process[session_key]["index"]=1
#    user_process[session_key]["return_value"]=""
#    user_process[session_key]["total"]=1
    
    processdata={}
#    processdata["process"]=1
#    processdata["index"]=1
#    processdata["return_value"]=""
#    processdata["total"]=1
#    cache.set(session_key,processdata,3600)
    
    
    
    try:
        if filetype=="txt" or filetype=="csv":                        
            fs=file(uploadpath+filename,"r")
            rec=fs.readline()#读取每行
            sheet_data = []
            ln=1
            while rec!="":
                if ln>=recordln:
                    rec=rec.decode(unicode_)
                    if rec.endswith("\r\n"):
                        rec=rec[:len(rec)-2]
                    linedata=rec.split(sparatorvalue)
                    ltmp=[]
                    for l in linedata:
                        if l.startswith('"') and l.endswith('"'):
                            ltmp.append(u"%s"%l[1:len(l)-1])
                        else:
                            ltmp.append(u"%s"%l)
                    sheet_data.append(ltmp)
                ln+=1
                rec=fs.readline()           
            fs.close()
            return sheet_data
        elif filetype == "xls" : # word 2007 xls文件后缀应该添加
            sheetdata=ParseXlsUxlrd(uploadpath+filename)
          #  global UPLOAD_FILEDATA
            #datash = UPLOAD_FILEDATA
            datash=sheetdata[0][1]
            #在运行开始让进度条 初始化为 0
            processdata['total'] = len(datash)#文件总数
            cache.set(session_key,processdata,3600)
#            user_process[session_key]['total'] = len(datash)#文件总数
#            deptfkey={}#部门外键存放的地方
#            hasdeptf=False
#            perfkey={}# 模型的数据存放的地方
#            for fld,value in fields.items():#遍历提交 对应关系
#                if fld.find(".")>0:
#                    fr=fld.split(".")
#                    if fr[0]=="Department":
#                        deptfkey[fr[1]]=value
#                else:
#                    perfkey[fld]=value
#                    
#            if deptfkey.has_key("code"):
#                hasdeptf=True
            
            
            for row in range(len(datash)):#每行每行开始读取
                if row==len(datash):
                    processdata["process"]=processdata["total"]
                    #变量
#                    user_process[session_key]["process"]=user_process[session_key]["total"]
                else:
                    processdata["process"] = processdata["process"]+1
                    #全局变量
#                    user_process[session_key]["process"] = user_process[session_key]["process"]+1
                cache.set(session_key,processdata,3600)
                try:
                   
                    if row>=recordln-1:#从第二行开始读取数据 
                        isSave=True #这里定义几个标识符 
                        has_property=False
                        strwhere={}
                        upobj=""
                        
                        
                        try:
                            for tmpfld,tmpfldvalue in fields.items():#fields.item() [(u'Department.code', 2), (u'EName', 1), (u'PIN', 0), (u'Department.name', 3)]
                                rf=""
                                #datash[1]=[[2, 1128.0], [1, u'\u5b8b\u7231\u73b2'], [1, u'2'], [1, u'\u90e8\u95e8\u540d\u79f0']], 
                                #datash[1][tmpfldvalue] 选取的是 数据对应的列 datash[row][tmpfldvalue][0]=1
                                if datash[row][tmpfldvalue][0]==2:#datsh[row]读取的每行数据 然后部选择对应的部门 编号所在的列
                                    dv=str(int(datash[row][tmpfldvalue][1]))
                                else:
                                    dv=datash[row][tmpfldvalue][1]# 为什么 判断，感觉没什么必要？？ dv=2
                                
                                if tmpfld.find(".")>0:#查找是否有外键的开始， 以.号 判断
                                    for f in model._meta.fields:#遍历循环（估计这个也最 消耗时间）
                                        if isinstance(f,ForeignKey):#匹配 外键  属性 也就是模型中的 每个数据对象
                                            if f.rel.to.__name__==tmpfld.split(".")[0]:#其中 f.rel.to.__name__ 是 模型下面的对象名称 如果找到了 tmpfld.split(".")[0]  = Department
                                                if str(dv).strip():#先strwhere = {'DeptID__code__exact':'1'}
                                                    strwhere[str(f.name+"__"+tmpfld.split(".")[1]+"__exact")]=dv.strip()#
                                                   
                                else:  
                                    if tmpfld=="code" and model==Department:
                                        strwhere={}
                                        strwhere["code__exact"]=datash[row][tmpfldvalue][1].strip()
                                        break
                                    if tmpfld=="PIN" and model==Employee:
                                        strwhere={}
                                        strwhere["PIN__exact"]=str(int(datash[row][tmpfldvalue][1])).strip()
                                        break 
                                    #strwhere[str(tmpfld+"__exact")]=datash[row][tmpfldvalue][1]=dv.strip()
                            #print strwhere
                            #print(Q(**strwhere))
                            upobj=model.objects.filter(Q(**strwhere))
                        except Exception, e:
                            logger.error("%s"%e)
                        if upobj:
                            obj=upobj[0]
                        else:
                            obj=model()
                        currelobj=[]
                        for fld,value in fields.items():
                            relObj=""
                            isForeignKey=False
                            if fld.find(".")>0:                                                     #查找到需要保存关联字段
                                for nkey,val in rlfield.items():                                 #查找关联记录,更新或创建,并保存
                                    if nkey.__name__==fld.split(".")[0]:
                                        strfilter={}
                                        for f  in fields:                                       #查找关联表多个相应的字段，并生成表达式
                                            if f.find(".")>0 :
                                                if f.split(".")[0]==nkey.__name__:
                                                    if datash[row][value][0]==2:
                                                        tmpvalue=str(int(datash[row][fields[f]][1]))
                                                    else:
                                                        tmpvalue=datash[row][fields[f]][1]
                                                    if tmpvalue.strip():
                                                        if f.split(".")[1]=="code" and model==Employee: 
                                                            strfilter={}  #人员表，查找部门表时，当有选择部门名称时，只需要查找部门编号                                                       
                                                            strfilter[str(f.split(".")[1]+"__exact")]=tmpvalue.strip()
                                                            break
                                                        else:
                                                            strfilter[str(f.split(".")[1]+"__exact")]=tmpvalue.strip()
                                        if strfilter:
                                            #print "strfilter:",strfilter
                                            dir(nkey)
                                            relObj=nkey.objects.filter(Q(**strfilter))
                                            
                                        if len(relObj)<=0:                              #查找不到记录，生成新记录
        #                                    print "not found"
                                            
                                            if addrelate!=1:
                                                isSave=False
                                                break                                                           #跳出当前行
                                            else:
                                                relObj=nkey()      
                                                is_save_rel=False                       
                                                for tfld in fields.keys():
                                                    if tfld.find(".")>0:
                                                        if tfld.split(".")[0]==nkey.__name__:
                                                            if datash[row][fields[tfld]][0]==2:
                                                                t_value=str(int(datash[row][fields[tfld]][1]))
                                                            else:
                                                                t_value=datash[row][fields[tfld]][1]
                                                            #print "t_value,",t_value
                                                            if t_value.strip():
                                                                relObj.__setattr__(tfld.split(".")[1],t_value.strip())
                                                                is_save_rel=True
                                                if is_save_rel:
                                                    
                                                    relObj.save()
                                                    relrecs.append(relObj)
                                                    isForeignKey=True
                                                else:
                                                    relObj=None
                                        else:
                                            isForeignKey=True
                                            relObj=relObj[0]
                                            #print "find: %s "%relObj.__doc__
                                        currelobj.append(relObj)
                                        break
                            if not isSave:
                                break                   #跳过当前行
                            tobj=""
                            fieldname=""
                            #print"%s:%s"%(fld,datash[row][value][1])
                            if isForeignKey:
                                for f  in obj._meta.fields:    #查找字段是否是外键
                                    if isinstance(f,ForeignKey) and  f.rel.to.__name__==fld.split(".")[0]:
                                        for tobj in currelobj:
                                            if tobj==f.rel.to:
                                                break        
                                        fieldname=f.name
                                        
                                        break
                                #print "%s :%s"%(fieldname,tobj.pk)
                                obj.__setattr__(fieldname,tobj)
                            else:
                                if datash[row][value][0]==2:
                                    cellvalue=str(int(datash[row][value][1]))
                                else:
                                    cellvalue=datash[row][value][1]
                                #print "field :%s    value:%s"%(fld,cellvalue)
                                if cellvalue.strip():
                                    if fld=="PIN":
                                        model_emp=sys.modules['mysite.personnel.models.model_emp']
                                        settings=sys.modules['mysite.settings']
                                        if len(str(cellvalue).strip())>getattr(settings,"PIN_WIDTH"):
                                            raise Exception(u"%s"%_(u"人员编号长度过长"))
                                        else:
                                            cellvalue=getattr(model_emp,"format_pin")(str(cellvalue.strip()))
                                    if fld=="code":
                                        dept=Department.objects.filter(code=cellvalue.strip())
                                        if dept:
                                            raise Exception(u"%s"%_(u'部门编号已存在'))
                                    obj.__setattr__(fld,cellvalue.strip())
                                    has_property=True
                        if isSave and has_property:
                            obj.save()
                            if(type(obj)==Employee):
                                if not obj.DeptID:#导入人员的时候 部门为空的时候 给默认的
                                    obj.__setattr__('DeptID',Department.objects.get(pk=1))
                                obj.__setattr__('attarea',(1,))
                                obj.save()
                            if(type(obj)==Department):
                                if obj.parent==None or obj.parent=="":                                        
                                     obj.parent_id=1
                                     obj.save()
                            objlist.append(obj)
                            
                except Exception,e:
                    #logger.error("%s"%e)
                    try:
                        error_list.append(str(row+1)+u"%s"%_(u" 行      ")+u"%s"%e)
                    except:
                        error_list.append(str(row+1))
                        pass
                    if errmode==1:                      # 按错误处理方式处理数据
                        continue                        
                    else:
                        raise
            
        else:
            pass
        
        if error_list:
            if len(error_list)>10:
                processdata["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list[:10]))+u"%s"%_(u"\n...\n还有%s条未显示，其它行导入操作成功！")%(len(error_list)-10))
                user_process[session_key]["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list[:10]))+u"%s"%_(u"\n...\n还有%s条未显示，其它行导入操作成功！")%(len(error_list)-10))
            else:
                processdata["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list))+u"%s"%_(u"\n出错，其它行导入操作成功！"))
                user_process[session_key]["return_value"]=(u"%s"%_(u"处理第\n")+u"%s"%("\n".join(error_list))+u"%s"%_(u"\n出错，其它行导入操作成功！"))
        else:
             processdata["return_value"]=(u"%s"%_(u"文件导入操作完成！"))
             user_process[session_key]["return_value"]=(u"%s"%_(u"文件导入操作完成！"))
        cache.set(session_key,processdata,3600)
#    processdata['error']=error_list
#    print processdata['error']
    except Exception, e:
        logger.error("%s"%e)
        if errmode==2:                  # 按错误处理方式处理数据
            j=0
            while j<len(objlist):                  #删除已保存记录
                objlist[j].delete()
            for ro in relrecs:          #删除关联表记录
                ro.delete()
        user_process[session_key]["return_value"]=(u"%s"%_(u"文件导入出错!"))
        cache.set(session_key,processdata,3600)
        user_process[session_key]["return_value"]=(u"%s"%_(u"文件导入出错!"))
    
def ParseXlsUxlrd(upload):
    '''
    #变量：upload —— 用户上传的excel文件
    #返回：返回一个列表，每一项就是一个表单(sheet)；
    #      其中表单是一个二元组(表单名称,表单数据)；
    #      而表单数据可以直接当做一个“二维数组”来看待，
    #      数组的内容即为二维空间内分布的单元格数据
    #      具体到单元格数据仍为一个二元组(单元格类型，单元格值)
    #      假设ExtractXls的返回值为 sheets
    #      则范例excel文件中的表单数为 len( sheets )
    #        表单n的名称为 sheets[ n ][0]
    #        表单n的数据为 sheets[ n ][1]
    #        表单n的行数为 len( sheets[ n ][1] )
    #        表单n的列数为 len( sheets[ n ][1][0] )
    #        表单n的i行j列的单元格数据为 sheets[ n ][1][ i ][ j ]

    #备注：现在对于合并的单元格还不能判断，无法提供样式支持；
    '''

    import xlrd
    try:
      book = xlrd.open_workbook(upload)
    except xlrd.XLRDError:
      return 0 

    sheets = [ ]
    for n in range(book.nsheets):
        sheet = [ ]
        sh = book.sheet_by_index(n)
        sh_data = [ ]
        for i in range(sh.nrows):
            row = [ ]
            for j in range(sh.ncols):
                cell = [ ]
                cell.append( sh.cell_type(rowx=i, colx=j) )
                cell.append( sh.cell_value(rowx=i, colx=j) )
                row.append( cell )
            sh_data.append( row )
        sheet.append( sh.name )
        sheet.append( sh_data )
        sheets.append( sheet )
    return sheets

def findAllFieldsAndModel(tablename,index_fields=[]):
    enq=Enquiry(tablename)
    tb=enq.findAllRelationTables()                #根据表名生成模型实例
    model=tb[0]  

    relatefield={}                                #关联表与主表字段影射
    fields={}
    list_display=[]
    if hasattr(model,"Admin"):
        daf=[]
        if hasattr(model.Admin,"import_fields"):
            daf=model.Admin.import_fields
        else:
            daf=model.Admin.list_display
        if daf:            
            for f in daf:
                if f.find("|")>0:
                    f=f.split("|")[0]
                if f.find(".")>0 or f.find("__")>0:
                    if f.find(".")>0:
                        f=f.split(".")[0]
                    if f.find("__")>0:
                        f=f.split("__")[0]
                list_display.append(f)
        #print "---daf:",daf
    
    for f_name in list_display:                
            fl =model._meta.get_field(f_name)
            if isinstance(fl,ForeignKey):            
                relatefield[fl.rel.to]=fl
                t=fl.rel.to
                f=fl
                #for t,f in relatefield.items():
                x=[]
                if hasattr(t.Admin,"import_fields"):
                    x=t.Admin.import_fields
                else:
                    x=t.Admin.list_display
                
                for fl in x:
                    if fl.find("|")>0:
                        fl=fl.split("|")[0]
                    if fl.find(".")>0 or fl.find("__")>0:
                        if fl.find(".")>0:
                            fl=fl.split(".")[0]
                        if f.find("__")>0:
                            fl=fl.split("__")[0]
                    
                    fl=t._meta.get_field(fl)
                    if isinstance(fl,ForeignKey) and fl.rel.to==t:
                        pass
                    else:
                        fields[t.__name__+"."+fl.name]=u"%s.%s"%(f.verbose_name,fl.verbose_name)
                        index_fields.append(t.__name__+"."+fl.name)
                
            else:
                index_fields.append(fl.name)
                fields[fl.name]= u"%s"%fl.verbose_name

    return (model,fields,relatefield)
            
    

def show_export(request,app_label,model_name):
    models={}
    filetype={}
    template={}
    #models["Employee"]=_("Employee Table")
    #models["Department"]=_("Department Table")
    rn=request.REQUEST.get("reportname",'')    
    if app_label!="list":    
        models[model_name]=rn and rn or GetModel(app_label,model_name)._meta.verbose_name
    else:
        models[model_name]=rn and rn or model_name
    filetype["txt"]=_(u"TXT 文件")
    filetype["csv"]=_(u"CSV 文件")
    filetype["pdf"]=_(u"PDF 文件")
    filetype["xls"] = _(u"EXCEL 文件")
    #filetype["json"]=_("JSON File")
    template["stdemployee"]=_(u"标准的员工模板")
    template["smpemployee"]=_(u"简单的雇员的模板")
    template["stddepartment"]=_(u"指纹模板")
    template["standard"]=_(u"标准模板")
    tables={'Employee':_(u'人员'),'department':_(u'授权部门')}

    return render_to_response('export.html', {
            'models': models,
            'filetype': filetype,
            'template': template,
            'filecoding':filecoding,
            'model_name':model_name,
            })
    
def file_export(request,app_label,model_name):       
    
    exportpath=settings.ADDITION_FILE_ROOT+"/"
    #print exportpath
    filename=""
    filetype=""
    model=""
    templatename=""
    filecode=""
    viewname=""
    
    data=dict(request.POST)
    filetype=str(data["filetype"][0])
    model=str(data["model"][0])
    templatename=data["templatename"][0].decode("utf-8")
    filecode=str(data["filecode"][0])
    viewname=str(data["txtviewname"][0])
    op=threadlocals.get_current_user()
   
    dtstr=""
    dt=datetime.now()
   
    dtstr=str(dt.year)+str(dt.month)+str(dt.day)+str(dt.hour)+str(dt.minute)+str(dt.second)
    
    Displayfileds=""                                #导出字段列表,可从视图中提取,或定制
    data=[]
    tblname=""
    model=GetModel(app_label,model_name)
    if viewname:
        from viewmodels import get_view_byname_js
        Displayfileds =get_view_byname_js[viewname]["fields"]
        
        
    if filetype=='txt':
        try:
            if templatename=='stdemployee':
                tblname="emp"
                Displayfileds=["id","EName","Gender","DeptID"]
                data=Employee.objects.all().values_list(*Displayfileds).order_by("id")

            elif templatename=='smpemployee':
                Displayfileds=["id","EName","Gender","DeptID"]
                data=Employee.objects.all().values_list(*Displayfileds).order_by("id")
                tblname="emp"
            elif templatename=='stddepartment': 
                Displayfileds=["DeptID","DeptCode","DeptName","parent"]
                data=Department.objects.all().values_list(*Displayfileds).order_by("DeptID")
                tblname="dep"
            else:
                Displayfileds=[fl.name for fl in model._meta.fields]
                data=model.objects.all().values_list(*Displayfileds).order_by("id")
                tblname=model.__name__
            #print "%s"%data
            filename=op.username+dtstr+tblname+"."+filetype

            ret= render_to_string(templatename+".txt", {
                    'fields': Displayfileds,
                    'tdata': data,
                    })
            f=file(exportpath+filename,'w')
            f.write(ret.encode(filecode))
            f.close()
            #print ret
            response = HttpResponse(ret,mimetype='application/octet-stream')   
            response['Content-Disposition'] = 'attachment; filename=%s' % filename  
            return response  
            
            
#           return HttpResponseRedirect("/data/file/%s"%filename)
            
            
#            response = HttpResponse(mimetype='text/csv')
#            response['Content-Disposition'] = 'attachment; filename=%s' % filename
#            
#            t = loader.get_template(templatename+".txt")
#            c = Context({
#                'tdata': data,
#                'fields': Displayfileds,
#            })
#            response.write(t.render(c))
#            return response
            
        except:
            import traceback; traceback.print_exc()
    elif filetype=='xls':
        pass
    elif filetype=='pdf':
        pass
    else:
        pass
    return HttpResponse(u"%s"%_(u"文件导入操作完成！"))
    
    
def detailprogress(request):
    global SESSION_PRO_KEY
    if SESSION_PRO_KEY:
        sess_key = SESSION_PRO_KEY
    else:
        sess_key=request.session.session_key+"process"
    Result={}
    processdata=cache.get(sess_key)#0610 ycm 修改进度条 使用缓存存储
    if processdata:
        if processdata['process'] == processdata['total']:
            processdata['index'] = 0
        process = int((processdata['process']*100)/processdata['total'])
        Result['index'] = processdata['index']
        Result['progress']=process
        Result['return_value'] = processdata['return_value']
       
        if process>= 100:
            process=100
            Result['index']=0 #标识符号 ，当为0 就不再来请求
            Result['progress']=100 #进度
            Result['return_value'] = processdata['return_value']#导入结束后提示信息
            cache.delete(sess_key)
            SESSION_PRO_KEY = ""
        return getJSResponse(smart_str(simplejson.dumps(Result)))
        
    else:
        Result['index']=1
        Result['progress']=0
        Result['return_value']=""
        return getJSResponse(smart_str(simplejson.dumps(Result)))
        