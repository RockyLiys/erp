# -*- coding: utf-8 -*-
import traceback
import string
import datetime
import os
from django.http import HttpResponse
from django.conf import settings
from django.core.cache.backends.filebased import CacheClass

def set_cookie(response, key, value, expire=None):
        if expire is None:
                max_age = 365*24*60*60  #one year
        else:
                max_age = expire
                expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age), "%a, %d-%b-%Y %H:%M:%S GMT")
        response.set_cookie(key, value, max_age=max_age, expires=expires,
                domain=settings.SESSION_COOKIE_DOMAIN,
                secure=settings.SESSION_COOKIE_SECURE or None)


def tmpDir():
        ret=settings.LOG_DIR
        try:
                os.makedirs(ret)
        except: pass
        return ret

def unquote(s):
    """unquote('abc%20def%u4E66') -> 'abc def'."""
    res = s.split('%')
    for i in xrange(1, len(res)):
        item = res[i]
        try:
                        if item[0]=='u':
                                res[i]=unichr(string.atoi(item[1:5],16))+item[5:]
                        else:
                                res[i] = chr(string.atoi(item[:2],16)) + item[2:]
        except KeyError:
            res[i] = '%' + item
        except UnicodeDecodeError:
            res[i] = unichr(int(item[:2], 16)) + item[2:]
    return "".join(res)

def appendFile(s):
        f=file("%s/info_%s.txt"%(tmpDir(),datetime.datetime.now().strftime("%Y%m%d")), "a+")
        try:
                f.write(s)
        except:
                try:
                        f.write(s.encode("utf-8"))
                except: pass
        f.write("\n")

def tmpFile(name, text, append=True):
        fn="%s/%s"%(tmpDir(),name)
        f=file(fn, append and "a+" or "w+")
        try:
                f.write(text)
        except:
                try:
                        f.write(text.encode("utf-8"))
                except: pass
        f.write("\n")
        f.close()
        return fn

def save_tmp_file(name, object):
    CacheClass(tmpDir(), {"max_entries":1024}).set(name, object,3600)

def load_tmp_file(name):
    return CacheClass(tmpDir(), {"max_entries":1024}).get(name)
    

def errorLog(request=None):
        f=file("%s/error_%s.txt"%(tmpDir(),datetime.datetime.now().strftime("%Y%m%d")), "a+")
        f.write("---%s: "%datetime.datetime.now());
        if request:
                f.write("-- %s%s --\n"%(request.META["REMOTE_ADDR"],request.META["PATH_INFO"]))
#        for v in request.REQUEST: f.write("\t%s=%s\n", v, request.REQUEST[v])
                f.write(request.raw_post_data)
        f.write("\n")
        traceback.print_exc(file=f)
        f.write("---------------------------------\n")
        try:
                traceback.print_exc()
        except: pass

def trim0(s):
    while(s[-1]=="\x00"): s=s[:-1]
    return s

def trimTemp(tmp):
        return tmp
        try:
                tmp=tmp.decode("base64")
        except:
                appendFile(tmp)
                errorLog()
        tmp=trim0(tmp)
        return tmp.encode("base64")

def getJSResponse(content=None):
        response = HttpResponse(mimetype="application/javascript")
        response["Pragma"]="no-cache"
        response["Cache-Control"]="no-store"
        response["Content-Type"]="application/javascript; charset="+settings.NATIVE_ENCODE
        if content:
                try:
                        content=unicode(content).encode(settings.NATIVE_ENCODE)
                except:
                        content=content.decode('utf-8').encode(settings.NATIVE_ENCODE)
                if type(content)==type({}):
                        from django.utils import simplejson
                        content=simplejson.dumps(content)
                response["Content-Length"]=len(content);
                response.write(content)
        return response

def today():
        d=datetime.datetime.now()
        return datetime.datetime(d.year,d.month,d.day)

def nextDay():
        d=datetime.datetime.now()
        d=d+datetime.timedelta(1,0)
        return datetime.datetime(d.year,d.month,d.day)

def endOfDay(d):
        d=d+datetime.timedelta(1,0)
        return datetime.datetime(d.year,d.month,d.day)-datetime.timedelta(0,1)

def startOfDay(d):
        return datetime.datetime(d.year,d.month,d.day)

def decodeTimeInt(t):
        tm_sec=t % 60;
        t/=60;
        tm_min=t % 60;
        t/=60;
        tm_hour=t % 24;
        t/=24;
        tm_mday=t % 31+1;
        t/=31;
        tm_mon=t % 12
        t/=12;
        tm_year=t+2000;
        return "%04d-%02d-%02d %02d:%02d:%02d"%(tm_year,tm_mon+1,tm_mday,tm_hour,tm_min,tm_sec)

def decodeTime(data):
        t=ord(data[0])+(ord(data[1])+(ord(data[2])+ord(data[3])*256)*256)*256
        return decodeTimeInt(t)

def encodeTime(y,m,d,hour,min,sec):
        tt=((y-2000)*12*31+((m-1)*31)+d-1)*(24*60*60)+(hour*60+min)*60+sec;
        return tt




def getAvialibleDB():
        import django
        dbs=[f for f in os.listdir(django.db.backends.__path__[0]) if not f.startswith('_') and not f.startswith('.') and not f.endswith('.py') and not f.endswith('.pyc')]
        dbs.remove('dummy')
        try:
                dbs.remove('mysql_old')
        except: pass
        try:
                import ado_mssql
                dbs.append('ado_mssql')
        except:        pass
        return dbs

def packList(l):
        r=[]
        for i in l:
                if i: r.append(i)
        return r

#设置操作系统的自动化任务
def scheduleTask(cmd, time="00:00", weeks=('Su', 'M', 'T', 'W', 'Th', 'F', 'Sa')):
        l=os.popen("at").read()
        for s in l.split("\n"):
                r=packList(s.split(" "))
                if len(r)>=4:
                        try:
                                int(r[0])
                        except:
                                r.pop(0)
                        atcmd=" ".join(r[3:])
                        if cmd.lower()==atcmd.lower() or cmd[1:-1].lower()==atcmd.lower():
                                print "Delete old schedule"
                                os.system("at %s /DELETE"%r[0])
        if weeks:
                dur=" /EVERY:"+(",".join(weeks))
        else:
                dur=""
        cmd="at %s%s %s"%(time, dur, cmd)
#        print cmd
        os.system(cmd)

