import re
import json
import MySQLdb
import type_check
from loggingex import LOG_WARNING
from loggingex import LOG_INFO

class mysql_conn():
    def __init__(self, host_name, port_num, user_name, password, db_name, charset_name = "utf8"):
        try:
            self._conn = MySQLdb.connect(host = host_name, port = int(port_num), user = user_name, passwd = password, db = db_name, charset = charset_name)
            LOG_WARNING("connect mysql %s:%d %s" % (host_name, port_num, db_name))
        except Exception as e:
            LOG_WARNING("connect mysql %s:%d %s error" % (host_name, int(port_num), db_name))
            conn = MySQLdb.connect(host=host_name, port=int(port_num), user=user_name,passwd=password)
            cursor = conn.cursor()
            sql = """create database if not exists %s""" %(db_name)
            LOG_INFO(sql)
            cursor.execute(sql)
            conn.select_db(db_name);
            conn.commit()
            cursor.close()
            conn.close()

        try:
            self._conn = MySQLdb.connect(host = host_name, port = int(port_num), user = user_name, passwd = password, db = db_name, charset = charset_name)
        except Exception as e:
            LOG_WARNING("connect mysql %s:%d %s error" % (host_name, int(port_num), db_name))
            return
        
        if None == self._conn:
            LOG_WARNING("connect mysql %s:%d %s error" % (host_name, int(port_num), db_name))
            return

        self.refresh_tables_info()

    def __del__(self):
        if self._conn:
            self._conn.close()
 
    def select(self, table_name, fields_array, conditions):
        cursor = self._conn.cursor()
        fields_str = "," . join(fields_array)
        conds = []
        for (column_name, column_data) in conditions.items():
            column_type = self._get_column_type(table_name, column_name)
            new_data = self._conv_data(column_data, column_type)
            cond = column_name + " = " + new_data
            conds.append(cond)
        conds_str = " and " . join(conds)

        sql = "select " + fields_str + " from " + table_name
        if len(conds_str) > 0:
            sql = sql + " where " + conds_str

        cursor.execute(sql)
        data_info = cursor.fetchall()
        cursor.close()
        return data_info

    def _get_tables_info(self):
        tables_info = {}
        cursor = self._conn.cursor()
        tables_sql = "show tables"
        cursor.execute(tables_sql)
        tables_name = cursor.fetchall()
        for table_name_item in tables_name:
            table_name = table_name_item[0]
            if 0 == len(table_name):
                continue
            columns_sql = "show columns from " + table_name 
            cursor.execute(columns_sql)
            table_info = cursor.fetchall()
            columns_info = self._get_table_info(table_info)
            if len(columns_info):
                tables_info[table_name] = columns_info
        cursor.close()
        return tables_info

    def _get_table_info(self, table_info):
        columns_info = {}
        for item in table_info:
            column_name = item[0]
            column_type_info = item[1]
            (type, len) = self._get_column_type_info(column_type_info)
            columns_info[column_name] = {"type":type, "length":len}
        return columns_info

    def _get_column_type_info(self, type_info):
        re_str = '(\w*)\((\d*),?.*\)'
        kw = re.findall(re_str, type_info)
        if len(kw):
            if len(kw[0]) > 1:
                return (kw[0][0], kw[0][1])
        return (None, None)

    def _implode(self, array_data, escape = False):
        array_str = ""
        for item in array_data:
            if 0 != len(array_str):
                array_str += ","
            if escape:
                if type_check.IsNumber(item) or type_check.IsFloat(item):
                    array_str += str(item)
                elif type_check.IsString(item):
                    array_str += "'"
                    array_str += item.encode("string_escape")
                    array_str += "'"
            else:
                array_str += str(item)
        array_str = "(" + array_str + ")"
        return array_str

    def _get_column_type(self, table_name, column_name):
        if table_name not in self._table_info.keys():
            return "None"
        if column_name not in self._table_info[table_name].keys():
            return "None"
        return self._table_info[table_name][column_name]["type"]
    
    def _conv_data(self, data, type):
        if type == "varchar" or type == "char":
            return '"%s"' % (data)
        elif type == "float":
            try:
                conv_data = float(data)
                return "%.2f"  % (conv_data)
            except Exception as e:
                LOG_WARNING("conv %s to %s error" % (data, type))
                return "0"
        elif type == "tinyint" or type == "bigint":
            return "%d" % (int(data))
    
    def _implode_by_tableinfo(self, data_array, table_name, columns_name_array):
        array_str = ""
        if len(data_array) != len(columns_name_array):
            LOG_WARNING("columns name length != data array length! %s %s " % (json.dumps(data_array), json.dumps(columns_name_array)))
            return ""

        for index in range(0, len(columns_name_array)):
            item = data_array[index]
            column_name = columns_name_array[index]
            column_type = self._get_column_type(table_name, column_name)
            if 0 != len(array_str):
                array_str += ","
            
            new_data = self._conv_data(item, column_type)
            array_str += new_data
        array_str = "(" + array_str + ")"
        return array_str
 
    def refresh_tables_info(self):
        self._table_info = self._get_tables_info()

    def insert_data(self, table_name, columns_name, data_array):
        columns = self._implode(columns_name)
        value_list = []
        for item in data_array:
            value_str = self._implode_by_tableinfo(item, table_name, columns_name)
            value_list.append(value_str)
        values_sql = ",".join(value_list)

        sql = "insert into " + table_name + columns + " values" + values_sql
        LOG_INFO(sql)
        self.excute(sql)

    def insert_onduplicate(self, table_name, data, keys_name):
        columns_name = data.keys()
        columns = self._implode(columns_name)
        value_list = []
        data_array = data.values()
        value_str = self._implode_by_tableinfo(data_array, table_name, columns_name)

        sql = "insert into " + table_name + columns + " values" + value_str
        
        update_data = {}
        for (column_name, column_data) in data.items():
            if column_name in keys_name:
                continue
            update_data[column_name] = column_data

        update_str_list = []
        for (column_name, column_data) in update_data.items():
            column_type = self._get_column_type(table_name, column_name)
            new_data = self._conv_data(column_data, column_type)
            update_str = column_name + "=" + new_data
            update_str_list.append(update_str)
        update_info_str = "," . join(update_str_list)

        if len(update_info_str) != 0:
            sql = sql + " ON DUPLICATE KEY UPDATE " + update_info_str
        LOG_INFO(sql)
        self.excute(sql)
    
    def has_table(self, table_name):
        if table_name in self._table_info.keys():
            return True
        return False

    def excute(self, sql):
        cursor = self._conn.cursor()
        try:
            cursor.execute(sql)
            self._conn.commit()
        except:
            LOG_WARNING("%s execute error" % (sql))
            self._conn.rollback()
        cursor.close()


if __name__ == "__main__":
    a = mysql_conn("127.0.0.1", 3306, "root", "fangliang", "stock")
    #a.insert_data("share_base_info", ["share_id", "share_name"], [["000123","2'xxx"], ["000345","'4yyy"]])
    #a.insert_onduplicate("share_base_info", {"share_id":"000123", "share_name":"4YYYYYYYYYYY"}, ["share_id"])
    a.select("share_base_info", ["share_id"], {"share_id":"000001"})

