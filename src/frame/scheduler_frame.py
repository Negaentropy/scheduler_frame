import os
import sys
import time
import ConfigParser

from loggingex import LOG_INIT
from loggingex import LOG_WARNING
from loggingex import LOG_DEBUG

from job_center import job_center
from singleton import singleton
from mysql_manager import mysql_manager
from mysql_conf_parser import mysql_conf_parser
from job_conf_parser import job_conf_parser
from scheduler_frame_conf_inst import scheduler_frame_conf_inst 

from j_load_job_conf import j_load_job_conf
from j_load_mysql_conf import j_load_mysql_conf
from j_load_regular_conf import j_load_regular_conf

@singleton
class scheduler_frame():
    def __init__(self, conf_path):
        os.chdir("../../")
        sys.path.append("src/")
        self._append_src_path("src/")

        reload(sys)
        sys.setdefaultencoding("utf8")

        self._frame_conf_inst = scheduler_frame_conf_inst()
        self._frame_conf_inst.load(conf_path)
        
        self._mysql_manager = mysql_manager()

        self._job_center = job_center()
        self._job_center.start()

    def _append_src_path(self, path):
        filelist =  os.listdir(path)  
        for filename in filelist:  
            filepath = os.path.join(path, filename)  
            if os.path.isdir(filepath):
                sys.path.append(filepath)
                self._append_src_path(filepath)  

    def _init_log(self):
        section_name = "frame_log"
        option_name = "conf_path"
        if False == self._frame_conf_inst.has_option(section_name, option_name):
            print("no %s %s" % (section_name, option_name))
            return
        conf_path = self._frame_conf_inst.get(section_name, option_name)
        print("Load %s %s %s" % (section_name, option_name, conf_path))
        LOG_INIT(conf_path)

    def _start_jobs(self):
        j_load_job_conf_obj = j_load_job_conf()
        j_load_job_conf_obj.run()
    
    def _init_db(self):
        j_load_mysql_conf_obj = j_load_mysql_conf()
        j_load_mysql_conf_obj.run()

    def _init_regular(self):
        j_load_regular_conf_obj = j_load_regular_conf()
        j_load_regular_conf_obj.run()
    
    def start(self):
        self._init_log()
        self._init_regular()
        self._init_db()
        self._start_jobs()

if __name__ == "__main__":
    a = scheduler_frame("./conf/frame.conf")
    a.start()
    while (1):
        time.sleep(1000)
