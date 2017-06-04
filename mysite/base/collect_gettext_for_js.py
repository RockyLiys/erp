# -*- coding: utf-8 -*-

from django.conf import settings
import os
import re
from django.utils.encoding import force_unicode
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


# 把*.js,*.html中gettext要翻译的前端字符串提取出来写到文件gettext_for_trans.js中
def gettext_for_trans():
    list_trans_str = []
    wp = settings.WORK_PATH
    dirs = list(settings.TEMPLATE_DIRS)
    dirs.append(wp + os.sep + "media" + os.sep + "jslib")
    str_arrays = []
    count_files = 0
    file_names = []
    count_catalog = 0
    svndirs = []
    try:
        for d in dirs:
            for root, dirs, files in os.walk(d):
                if (os.path.split(root)[1] in [".svn"]) or [e for e in svndirs if root.find(e) != -1]:
                    svndirs.append(root)
                    continue
                if files:
                    count_files = count_files + len(files)
                    file_names = file_names + files
                    for vfileName in files:
                        fileName = os.path.join(root, vfileName)
                        f = open(fileName, "r")
                        sread = force_unicode(f.read())
                        f.close()
                        str_tmp = re.findall(r'''gettext\(".*?"\)|gettext\('.*?'\)''', sread)
                        count_catalog = count_catalog + len(str_tmp)
                        if str_tmp:
                            str_arrays.append("//in file--%s" % fileName)
                        for e in str_tmp:
                            key = e[e.find("gettext(") + 9:-2]
                            str_arrays.append('catalog["' + key + '"] = "";')
    except:
        import traceback;
        traceback.print_exc();

    print('exclude')
    print("\n".join(svndirs))
    tmp_arrays = []
    while True:
        if str_arrays:
            if str_arrays[0] not in tmp_arrays:
                tmp_arrays.append(str_arrays[0])
                # else:
                #  tmp_arrays.append("//"+str_arrays[0])

            str_arrays = str_arrays[1:]
        else:
            break
    f = open("gettext_for_trans.js", "a")

    buff = StringIO()
    temp = sys.stdout
    sys.stdout = buff
    str_arrays = tmp_arrays
    for e in str_arrays:
        print(e)
    sys.stdout = temp
    f.write(buff.getvalue().encode("utf8"))
    f.close()

    print('count files %s, count catalog %s' % (count_files, count_catalog))
