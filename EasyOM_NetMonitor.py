#!/usr/local/bin python
# -*- coding: utf-8 -*-

import requests as rq
import time
import cx_Oracle as ora
import os
import psutil
import time
import platform

os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

class Prog(object):
    def __init__(self):
        self.ipList = list()
        #self.alias = "未知服务器"
        self.tns = "om/om@localhost:1521/orcl"
        self.__loadConfig()
        #print(self.alias)

    def __loadConfig(self):
        with open("nmconfig.conf", "r", encoding='utf-8-sig') as f:
            temp = f.read()
        
        infoo = temp.split("========")[0]
        tnss = temp.split("========")[1]

        infoList = infoo.split("----")

        for info in infoList:
            if "alias : " in info and "ip : " in info:
                dd = dict()
                rowList = info.split("\n")
                for row in rowList:
                    if " : " in row:
                        tList = row.split(" : ")
                        dd[tList[0].strip()] = tList[1].strip()
                if "alias" in dd.keys() and "ip" in dd.keys():
                    self.ipList.append(dd)
        
        print(self.ipList)

        if "tns : " in tnss:
            self.tns = tnss.split("tns : ")[-1].strip()
        
        print(self.tns)

    def netMonitor(self):
        try:
            db = ora.connect(self.tns)
            cr = db.cursor()
        except:
            print("数据库连接失败")
        if "windows" in platform.system().lower():
            isWin = True
        else:
            isWin = False

        for ip in self.ipList:
            now = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))

            if isWin:
                result = os.system("ping %s -n 1" % ip["ip"])
            else:
                result = os.system("ping %s -c 1" % ip["ip"])

            print(now)

            if result:
                print("\t服务器 %s 网络连接异常" % ip["alias"])
                sql = """
                insert into om_network
                values (
                    '%s', '%s', '异常', null, to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (
                    ip["alias"], ip["ip"], now
                )
            else:
                print("\t服务器 %s 网络连接正常" % ip["alias"])
                sql = """
                insert into om_network
                values (
                    '%s', '%s', '正常', null, to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (
                    ip["alias"], ip["ip"], now
                )
            
            try:
                cr.execute(sql)
                db.commit()
            except:
                pass
        
        try:
            cr.close()
            db.close()
        except:
            pass    

if __name__ == "__main__":
    prog = Prog()

    #prog.netMonitor()

    while True:
        #print(time.strftime('%Y-%m-%d %X',time.localtime()))
        prog.netMonitor()
        
        time.sleep(1800)

