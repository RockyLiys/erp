# -*- coding: utf-8 -*-
from django.db import models, connection
from django.db.models.fields import AutoField
from django.utils.translation import ugettext_lazy as _
import xlrd
import types
from django.db import connections, IntegrityError, DatabaseError
from mysite.utils import printf
from base.backup import get_attsite_file
u'''----------------------------------------------------------------------------
导入的步骤:   
    1、设计导入页面
    2、前端验证
    3、上传文件，以及辅助参数
    4、得到导入的模型
    5、后端验证文件格式
    6、是否有必填字段，如果头里面没有必填字段直接返回
    7、获取文件头，以及记录
    8、根据模型中的字段的verbose_name和文件头的字段，找出文件与模型字段的对应关系
    9、特殊字段的格式化，如人员编号需要根据attsite.ini里面PIN_WIDTH 格式化,有默认值的需要初始化为默认值
    10、批量把记录插入数据库,为了实现快速导入
    11、每一步都可以查看一下error_info属性中是否有错误信息，如果有错误信息则说明导入出现了问题
    12、重复记录的判断，是覆盖，还是不导入，最好是给唯一性约束的字段在数据库添加唯一性约束，不然
    重复的通过查数据库来判断是否有该记录已有重复，将是相当慢的。
--------------------------------------------------------------------------------
'''

class ImportData(object):
    def __init__(self,req,input_name = "import_data"):
        u"初始化基础类"
        self.input_name = "import_data" #前段上传文件控件的名称
        self.valid_format = ["xls","csv"] #导入的文件格式
        self.request=req #请求
        self.head = None #模型头
        self.records=[] #记录
        self.format = None #上传文件的格式
        self.upload_file = None #上传的文件
        self.app_label = None #应用名称
        self.model_name = None #模型名称
        self.model_cls = None #模型类
        self.error_info = [] #错误信息
        self.valid_head_indexs =[] #导入文件中合法字段的索引
        self.valid_model_fields = [] #导入文件中包含的模型字段
        self.other_fields = [] #其他需要没有在文档中的字段，使用默认值插入到数据
        self.calculate_fields_verbose = []# {u"%s"%_(u"部门编号"):""} 用来给其他列初始化的列，例如人员中的部门编号，就是为了初始化，人员中的部门字段
        self.calculate_fields_index = {}# 在文档头中的index
        #self.map_field_head = {} #模型字段的名称与导入文件的列的序号对应关系
        self.must_fields=[] #必须要用户填的字段，如员工的PIN号。。。
        self.current_dbtype = "sqlserver_ado" #当前连接数据库的驱动名称
        self.input_name = input_name
        self.need_read_data = True #默认需要从文件中读取数据
        self.need_update_old_record = self.request.POST.get("duplicate_pin",False) #已经存在的记录是否需要更新
        self.sql_batch_cnts = 80
        if self.need_update_old_record == u"0":
            self.need_update_old_record = False
        else:
            self.need_update_old_record = bool(self.need_update_old_record)
            
        app_label = self.request.POST.get("app_label",None)
        model_name = self.request.POST.get("model_name",None)
        #print "app_label:%s,model_name:%s\n"%(app_label,model_name)
        if  app_label and model_name:
            self.model_cls = models.get_model(app_label, model_name)
        else:
            self.error_info.append(u"%s"%_(u"模块参数错误"))
        cnts = get_attsite_file()["SYS"]["SQL_BATCH_CNTS"]
        if cnts:
            self.sql_batch_cnts = int(cnts)
    def validate_format(self):
        u"验证文件格式,True标示验证成功，False标示验证失败"
        ret = True
        if self.request.FILES:
            f=self.request.FILES[self.input_name]
            f_format=str(f).split('.')
            format_list=["txt","xls","csv",]
            try:
                format_list.index(str(f_format[1]))
                self.format = f_format[1]
                self.upload_file = f
            except:
                ret =False
                self.error_info.append(u"%s"%_(u"文件格式无效！"))
        else:
            ret =False
            self.error_info.append(u"%s"%_(u"请选择文件"))
        return ret

    def get_file_data(self):
        u"得到文件的头部数据和记录"
        ret = True
        #print 'self.format',self.format,'\n'
        if self.format == "xls":
            ret = self.xls_read()
        if self.format == "txt":
            ret = self.txt_read()
        if self.format == "csv":
            ret = self.csv_read()
        return ret
    
    def check_must_fields(self):
        if self.must_fields: #必须要的字段
            for e in self.must_fields:
                flag = False 
                for elem in self.head:
                    if elem == e:
                        flag = True
                        break
                if flag:
                    flag = False
                else:
                    self.error_info.append(u"%(nd)s"%{
                        "nd":_(u"文件中必须要%s字段")% e
                    })
                    return False
        
        return True
        
    def xls_read(self):
        u"读xls数据"
        try:
            fd = self.upload_file.read()
            book  = xlrd.open_workbook(file_contents=fd)
        except Exception,e:
            import traceback
            traceback.print_exc()
            self.error_info.append(u"%s"%_(u"文件格式错误:%s")%e)
            return False
        finally:
            self.upload_file.close()
       
        if book.nsheets != 1: #工作表必须是一张，减轻程序负担，也减轻客户错误的概率
            self.error_info.append(u"%s"%_(u"工作表只能为一张"))
            return False
        
        sh = book.sheet_by_index(0) #取第一张工作表
        sh_data = [ ]
        if sh.nrows<2:
            self.error_info.append(u"%s"%_(u"数据不能少于两条(标题和数据)"))
            return False
        
        for i in range(sh.nrows):
            row = [ ]
            for j in range(sh.ncols):
                v =  sh.cell_value(rowx=i, colx=j)
                if type(v) in(types.FloatType,types.IntType):
                    v= int(v)
                row.append(u"%s"%v)
            if i == 0: #第一行必须是头
                self.head  = row
                self.mapping_model()
                if not self.valid_head_indexs:
                    self.error_info.append(u"%s"%_(u"没有匹配的字段"))
                    return False
                
                ret = self.check_must_fields()
                if not ret:
                    return False
            else:
                sh_data.append( row )
        
        self.records = sh_data
        return True
    
    
    def simple_read(self,split_char = [",",]):
        u"默认txt,csv只支持,隔开,这个可以根据自己的需要自己重写"
        records = []
        try:
            all_data =self.upload_file.read().strip()#读取每行
            if not isinstance(all_data,unicode):
                try:
                    all_data = all_data.decode("utf-8")
                except:
                    all_data = all_data.decode("gb18030")
            if not all_data:
                self.error_info.append(u"%s"%_(u"文件数据不能为空"))
                return False
                
            rows = all_data.split("\r\n")
            
            if len(rows)<2:
                self.error_info.append(u"%s"%_(u"数据不能少于两条(标题和数据)"))
                return False
            
            for index in  range(len(rows)):
                row_list = rows[index].strip().split(split_char[0])#查找分隔符
                if index == 0:
                    self.head = [ e.strip() for e in rows[index].split(split_char[0])]
                    self.mapping_model()
                    ret = self.check_must_fields()
                    if not ret:
                        return False
                else:
                    records.append(row_list)
        finally:
            self.upload_file.close()
        
        self.records = records
        return True
    
    def txt_read(self):
        u"读txt文件"
        return self.simple_read()
    
    def csv_read(self):
        u"读csv文件"
        return self.simple_read()

        
    def insert_data(self):
        #根据不同的数据库 执行对应的sql语句
        try:
            if 'mysql' in connection.__module__:#mysql 数据库
                self.current_dbtype = "mysql"
                return self.mysql_insert()
            elif 'sqlserver_ado' in connection.__module__:#sqlserver 2005 数据库 
                self.current_dbtype = "sqlserver_ado"
                return self.sqlserver_insert()
            elif 'oracle' in connection.__module__: #oracle 数据库 
                self.current_dbtype = "oracle"
                return self.oracle_insert()
            elif 'postgresql_psycopg2' in connection.__module__: # postgresql 数据库
                self.current_dbtype = "postgresql_psycopg2"
                return self.postgresql_insert()
        except Exception,e:
            import traceback
            traceback.print_exc()
            self.error_info.append(u"%s"%'导入时出现数据库错误，请检查数据有效性')
#            self.error_info.append(u"%s"%e)
        return False
    
    def get_db_value(self,tmp_field,tmp_value):
        u"分析字段和值，得到正确的数据库值"
        if not tmp_value:
            if tmp_value in (True,False):
                tmp_value = u'%s'%int(tmp_value)
            else:
                dfvalue = tmp_field.get_default()
                if dfvalue != None:
                    tmp_value = u'%s'%dfvalue
                else:
                    tmp_value = None
        else:
            tmp_value = u'%s'%tmp_value
        return tmp_value

    def mapping_model(self):
        u"找到模型对象的字段对应导入文件中的头的列序号"
        valid_head_indexs = [] #有效的头的索引
        valid_model_fields =[] #有效的头的索引所对应的模型字段
        fields = self.model_cls._meta.fields
        other_fields = []
        calculate_fields_index = {} #用于计算的字段
        for index in range(len(self.head)):
            head_elem = self.head[index].strip()
            if head_elem in self.calculate_fields_verbose and head_elem not in calculate_fields_index:
                calculate_fields_index[ head_elem ] = index
            for f in fields:
                if type(f) != AutoField: #排除多对多
                    verbose_name = u"%s"%f.verbose_name
                    if verbose_name == head_elem:
                        valid_head_indexs.append(index)
                        valid_model_fields.append(f)
                    
        for f in fields:
            if f not in valid_model_fields:
                if type(f) != AutoField: #排除多对多
                    other_fields.append(f)
        self.valid_head_indexs = valid_head_indexs
        self.valid_model_fields = valid_model_fields 
        self.other_fields =  other_fields
        self.calculate_fields_index = calculate_fields_index
        
        if self.valid_head_indexs:
            return True
        
        return False
    
    def before_insert(self):
        u"插入前的准备,提供给特殊处理"
        return True
    
    def records_analysis(self,record_dict):
        u"分析插入的数据"
        return True
    
    def postgresql_insert(self):
        u"sqlserver 数据插入"
        model_table = self.model_cls._meta.db_table
        v_f_db_names  = [ e.get_attname_column()[1] for e in self.valid_model_fields ]#上传的文件中拥有的字段
        o_f_db_names  = [ e.get_attname_column()[1] for e in self.other_fields ]#模型中其他的字段
        
        cursor = connection.cursor()
        count_head = len(self.head) 
        sql_list = []
        for row in self.records:
            row_fields_select = {}
            calculate_dict = {}
            count_v = 0
            for index in range(count_head):
                for k,v in self.calculate_fields_index.items():
                    if v == index:
                        calculate_dict[ k ] = row[index]
                
                if index in self.valid_head_indexs:#在文档中的字段
                    tmp_value = row[index]
                    tmp_field = self.valid_model_fields[count_v]
                    if tmp_field.choices:
                        tv = [ e[0] for e in tmp_field.choices if e[1] == tmp_value ] #通过verbose_name得到实际数据库的值
                        if tv:
                            tmp_value = tv[0]
                    key = v_f_db_names[count_v]
                    value = self.get_db_value(tmp_field,tmp_value)
                    if key == "badgenumber" and not value:#人员编号为空，去掉这条记录， 会出现脏数据？？？？？
                        break
                    key = '"'+v_f_db_names[count_v]+'"'
                    row_fields_select[key] =  value
                    count_v = count_v +1
            
            count_o = 0
            for f in self.other_fields:#不在文档中的字段
                default_value = f.get_default()
                if default_value == None:
                    default_value = None
                else:
                    if default_value in (True,False):
                        default_value = u'%s'%int(default_value)
                    else:
                        default_value = u'%s'%default_value
                key = '"'+o_f_db_names[count_o]+'"'
                row_fields_select[ key ] = default_value
                count_o = count_o + 1
                
            row_fields_select = self.process_row(row_fields_select,calculate_dict) #处理每一行的接口
            
            sql_list.append(row_fields_select)
            if len(sql_list) == self.sql_batch_cnts:
                cursor = connection.cursor()
                self.exe_sqlserver(cursor,model_table,sql_list)
                cursor.close()
                sql_list = []
        
        if sql_list:
            cursor = connection.cursor()
            self.exe_sqlserver(cursor,model_table,sql_list)
            cursor.close()
        try:
            connection._commit()
        except:
            pass
        
    def sqlserver_insert(self):
        u"sqlserver 数据插入"
        model_table = self.model_cls._meta.db_table
        v_f_db_names  = [ e.get_attname_column()[1] for e in self.valid_model_fields ]#上传的文件中拥有的字段
        o_f_db_names  = [ e.get_attname_column()[1] for e in self.other_fields ]#模型中其他的字段
        
        cursor = connection.cursor()
        count_head = len(self.head) 
        sql_list = []
        for row in self.records:
            row_fields_select = {}
            calculate_dict = {}
            count_v = 0
            for index in range(count_head):
                for k,v in self.calculate_fields_index.items():
                    if v == index:
                        calculate_dict[ k ] = row[index]
                
                if index in self.valid_head_indexs:#在文档中的字段
                    tmp_value = row[index]
                    tmp_field = self.valid_model_fields[count_v]
                    if tmp_field.choices:
                        tv = [ e[0] for e in tmp_field.choices if e[1] == tmp_value ] #通过verbose_name得到实际数据库的值
                        if tv:
                            tmp_value = tv[0]
                    key = v_f_db_names[count_v]
                    value = self.get_db_value(tmp_field,tmp_value)
                    if key == "badgenumber" and not value:#人员编号为空，去掉这条记录， 会出现脏数据？？？？？
                        break
                    row_fields_select[key] =  value
                    count_v = count_v +1
            
            count_o = 0
            for f in self.other_fields:#不在文档中的字段
                default_value = f.get_default()
                if default_value == None:
                    default_value = None
                else:
                    if default_value in (True,False):
                        default_value = u'%s'%int(default_value)
                    else:
                        default_value = u'%s'%default_value
                key = o_f_db_names[count_o]
                row_fields_select[ key ] = default_value
                count_o = count_o + 1
                
            row_fields_select = self.process_row(row_fields_select,calculate_dict) #处理每一行的接口
            
            sql_list.append(row_fields_select)
            if len(sql_list) == self.sql_batch_cnts:
                self.exe_sqlserver(cursor,model_table,sql_list)
                sql_list = []
        
        if sql_list:
            self.exe_sqlserver(cursor,model_table,sql_list)
            
        try:
            connection._commit()
        except:
            pass
        
    def exe_sqlserver(self,cursor,model_table,sql_list):
        u"当批量插入报错后，改为一条一条插入"
        INSERT_SQL =u"INSERT INTO %(table)s ( %(fields)s ) VALUES ( %(row)s )"
        UPDATE_SQL = "UPDATE  %(table)s SET %(fields_value)s WHERE %(condition)s"
        update_records = []
        insert_records = sql_list#格式：[{},{}]
        ret ={
            "INSERT_SQL": INSERT_SQL,
            "UPDATE_SQL":UPDATE_SQL,
            "update_records":update_records,
            "insert_records":insert_records,
            "sql_list":sql_list,
            "model_table":model_table,
            "update_old_record":self.need_update_old_record,
        }
    
        self.records_analysis( ret )#分析的接口
        
        if ret["insert_records"]:#插入
            temp_insert_records = []#最终的批量sql语句
            params = []#批量sql的参数
            multi_sql_params = []#批量出错，存储所有的参数
            for record in ret["insert_records"]:
                field_count = len(record.keys())
                sql_param = ""#参数个数，%s
                for i in range(field_count):
                    sql_param += "%s,"
                sql_param = sql_param[:-1]#去掉最后的 ,号
                
                insert_sql= INSERT_SQL%{
                    "table":model_table,
                    "fields":u",".join(record.keys()),
                    "row":sql_param
                    }
                param = [v for v in record.values()]
                params += param
                multi_sql_params.append(param)
                temp_insert_records.append(insert_sql)

            try:
                insert_sql = ";".join(temp_insert_records)
                params = tuple(params)
                cursor.execute(insert_sql, params)
            except IntegrityError:
                #print '---------has--emp------'
                for i, sql in enumerate(temp_insert_records):
                    try:
                        if multi_sql_params and multi_sql_params[i]:
                            cursor.execute(sql, multi_sql_params[i])
                    except:
                        pass
#            except Exception, e:
#                print '---------eeee=', e
                   
        if self.need_update_old_record and ret["update_records"] and ret["update_records"][0]:#更新需要自己构造好SQL
            update_records = ret["update_records"] and ret["update_records"][0]
            params = ret["update_records"] and ret["update_records"][1]
            multi_params = ret["update_records"] and ret["update_records"][2]
            try:
                update_sql = ";".join(update_records)
                params = tuple(params)
                cursor.execute(update_sql, params)
            except IntegrityError:
                for i, sql in enumerate(update_records):
                    try:
                        if multi_params and multi_params[i]:
                            cursor.execute(sql, multi_params[i])
                    except:
                        pass
#            except Exception, e:
#                print '----------------update---sql----eeee=', e 
        
        
    def mysql_insert(self):
        u"mysql 数据插入"
        model_table = self.model_cls._meta.db_table
        v_f_db_names  = [ e.get_attname_column()[1] for e in self.valid_model_fields ]
        o_f_db_names  = [ e.get_attname_column()[1] for e in self.other_fields ]
        
       
        count_head = len(self.head) 
        sql_list = []
        calculate_dict = {}
        insert_keys = []
        for row in self.records:
            row_fields_select = {}
            count_v = 0
            for index in range(count_head):
                for k,v in self.calculate_fields_index.items():
                    if v == index:
                        calculate_dict[ k ] = row[index]
                
                if index in self.valid_head_indexs:
                    tmp_value = row[index]
                    tmp_field = self.valid_model_fields[count_v]
                    if tmp_field.choices:
                        tv = [e[0] for e in tmp_field.choices if e[1] == tmp_value ] #通过verbose_name得到实际数据库的值
                        if tv:
                            tmp_value = tv[0]
                    key = v_f_db_names[count_v]
                    value = self.get_db_value(tmp_field,tmp_value)
                    row_fields_select[key] = value
                    count_v = count_v +1
            
            count_o = 0
            for f in self.other_fields:
                default_value = f.get_default()
                if default_value == None:
                    default_value = None
                else:
                    if default_value in (True,False):
                        default_value = u'%s'%int(default_value)
                    else:
                        default_value = u'%s'%default_value
                key = o_f_db_names[count_o]
                row_fields_select[key]=default_value
                count_o = count_o + 1
            
            row_fields_select = self.process_row(row_fields_select,calculate_dict) #处理每一行的接口
            sql_list.append( row_fields_select )
            
            if not insert_keys :
                insert_keys = ",".join(row_fields_select.keys())
            if len(sql_list)>200:
                cursor = connection.cursor()
                self.exe_mysql(cursor,model_table,sql_list)
                cursor.close()
                sql_list = []
        
        if sql_list:
            cursor = connection.cursor()
            self.exe_mysql(cursor,model_table,sql_list)
            cursor.close()
        try:
            connection._commit()
        except:
            pass
        
    def exe_mysql(self,cursor, model_table, sql_list):
        u"当批量插入报错后，改为一条一条插入"
        INSERT_SQL =u"INSERT INTO %(table)s ( %(fields)s ) VALUES ( %(row)s )"
        UPDATE_SQL = "UPDATE  %(table)s SET %(fields_value)s WHERE %(condition)s"
        update_records = []
        insert_records = sql_list#格式：[{},{}]
        ret ={
            "INSERT_SQL": INSERT_SQL,
            "UPDATE_SQL":UPDATE_SQL,
            "update_records":update_records,
            "insert_records":insert_records,
            "sql_list":sql_list,
            "model_table":model_table,
            "update_old_record":self.need_update_old_record,
        }
    
        self.records_analysis( ret )#分析的接口
        
        if ret["insert_records"]:#插入
            temp_insert_records = []#最终的批量sql语句
            params = []#批量sql的参数
            multi_sql_params = []#批量出错，存储所有的参数
            for record in ret["insert_records"]:
                field_count = len(record.keys())
                sql_param = ""#参数个数，%s
                for i in range(field_count):
                    sql_param += "%s,"
                sql_param = sql_param[:-1]#去掉最后的 ,号
                
                insert_sql= INSERT_SQL%{
                    "table":model_table,
                    "fields":u",".join(record.keys()),
                    "row":sql_param
                    }
                param = [v for v in record.values()]
                params += param
                multi_sql_params.append(param)
                temp_insert_records.append(insert_sql)

            try:
                insert_sql = ";".join(temp_insert_records)
                params = tuple(params)
                cursor.execute(insert_sql, params)
            except IntegrityError:
#                print '---------has--emp------'
                for i, sql in enumerate(temp_insert_records):
                    try:
                        if multi_sql_params and multi_sql_params[i]:
                            cursor.execute(sql, multi_sql_params[i])
                    except:
                        pass
#            except Exception, e:
#                print '---------eeee=', e
                   
        if self.need_update_old_record and ret["update_records"] and ret["update_records"][0]:#更新需要自己构造好SQL
            update_records = ret["update_records"] and ret["update_records"][0]
            params = ret["update_records"] and ret["update_records"][1]
            multi_params = ret["update_records"] and ret["update_records"][2]
            try:
                update_sql = ";".join(update_records)
                params = tuple(params)
                cursor.execute(update_sql, params)
            except IntegrityError:
                for i, sql in enumerate(update_records):
                    try:
                        if multi_params and multi_params[i]:
                            cursor.execute(sql, multi_params[i])
                    except:
                        pass
#            except Exception, e:
#                print '----------------update---sql----eeee=', e 
        
            
#            try:
#                update_sql = u";".join(ret["update_records"])
#                cursor.execute(update_sql)
#            except IntegrityError:
#                for sql in ret["update_records"]:
#                    try:
#                        cursor.execute(sql)
#                    except:
#                        pass
 

    
    def after_insert(self):
        u"插入之后"
        return True
    def process_row(self,row_data,calculate_dict):
        u"特殊情况给开发人员提供的接口"
        return row_data
    def oracle_insert(self):
        u"oracle 数据插入"
        pass
    
    def postgresql(self):
        u"postgresql 数据插入"
        pass
    
    def exe_import_data(self):
        u"导入默认流程,成功返回True,不成功返回False,错误信息存储在error_info列表中"
        if self.error_info:
            return False
        if self.need_read_data:#是否需要从文件中读取数据
            self.validate_format()
            if self.error_info:
                return False
            
            self.get_file_data()
            if self.error_info:
                return False
        
        self.before_insert()
        if self.error_info:
            return False

        self.insert_data()
        if self.error_info:
            return False
        
        self.after_insert()
        if self.error_info:
            return False
        
        
