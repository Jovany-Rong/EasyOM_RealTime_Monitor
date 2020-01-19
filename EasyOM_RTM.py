#!/usr/local/bin python
# -*- coding: utf-8 -*-

import requests as rq
import time
import cx_Oracle as ora
import os
import psutil
import time

os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

class Prog(object):
    def __init__(self):
        self.tomList = list()
        self.alias = "未知服务器"
        self.tns = "om/om@localhost:1521/orcl"
        self.__loadConfig()
        #print(self.alias)

    def __loadConfig(self):
        with open("rtmconfig.conf", "r", encoding='utf-8-sig') as f:
            temp = f.read()

        basicConf = temp.split("========")[0]

        rowList = basicConf.split("\n")
        
        dd = dict()

        for row in rowList:
            if " : " in row:
                tList = row.split(" : ")
                dd[tList[0].strip()] = tList[1].strip()

        if "alias" in dd.keys():
            self.alias = dd["alias"]

        if "tns" in dd.keys():
            self.tns = dd["tns"]

        tmctConf = temp.split("========")[1]

        tmctList = tmctConf.split("----")

        tomcats = list()

        for tmct in tmctList:
            if "ip_port" not in tmct:
                continue

            rowList = tmct.split("\n")
            
            dd = dict()

            for row in rowList:
                if " : " in row:
                    tList = row.split(" : ")
                    dd[tList[0].strip()] = tList[1].strip()

            if "ip_port" in dd.keys() and "username" in dd.keys() and "password" in dd.keys():
                tomcats.append(dd)

        self.conf = [tomcats]

    def tomcatInit(self):
        tomcats = self.conf[0]
        for tomcat in tomcats:
            tom = Tomcat(tomcat["ip_port"], tomcat["username"], tomcat["password"])
            self.tomList.append(tom)

    def tomcatCheck(self):
        for tom in self.tomList:
            print("Tomcat %s Check: " % tom.ipPort)
            if tom.probeLogin(tom.user, tom.password):
                checkTime = time.strftime('%Y-%m-%d %X',time.localtime())
                req = tom.reqCheck(tom.user, tom.password)
                jvm = tom.jvmCheck(tom.user, tom.password)

                print("\tRequest Count: %s" % req)
                print("\tJVM Check: " + str(jvm["MemoryUsed"]))

                try:
                    db = ora.connect(self.tns)
                    cr = db.cursor()
                    sql = """
                    insert into om_jkxx_middleware
                    values (
                        sys_guid(), '%s', %s, %s, %s, %s, %s, to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                    )
                    """ % (tom.ipPort, req, jvm["MemoryUsed"], jvm["FreeMemory"], jvm["TotalMemory"], jvm["MaxMemory"], checkTime)
                    cr.execute(sql)
                    db.commit()
                    cr.close()
                    db.close()
                except Exception as e:
                    print(e)

                if jvm["MemoryUsed"] > 70 and jvm["MemoryUsed"] <= 80:
                    try:
                        db = ora.connect(self.tns)
                        cr = db.cursor()
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '一般',
                            'JVM内存使用率超过70%%',
                            'TOMCAT',
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (tom.ipPort, checkTime)
                        cr.execute(sql)
                        db.commit()
                        cr.close()
                        db.close()
                    except Exception as e:
                        print(e)

                if jvm["MemoryUsed"] > 80 and jvm["MemoryUsed"] <= 90:
                    try:
                        db = ora.connect(self.tns)
                        cr = db.cursor()
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '严重',
                            'JVM内存使用率超过80%%',
                            'TOMCAT',
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (tom.ipPort, checkTime)
                        cr.execute(sql)
                        db.commit()
                        cr.close()
                        db.close()
                    except Exception as e:
                        print(e)

                if jvm["MemoryUsed"] > 90:
                    try:
                        db = ora.connect(self.tns)
                        cr = db.cursor()
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '危险',
                            'JVM内存使用率超过90%%',
                            'TOMCAT',
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (tom.ipPort, checkTime)
                        cr.execute(sql)
                        db.commit()
                        cr.close()
                        db.close()
                    except Exception as e:
                        print(e)
            else:
                print("\tFailed.")

    def systemCheck(self):
        print("System Check: ")
        dd = dict()

        checkTime = time.strftime('%Y-%m-%d %X',time.localtime())

        cpuPercent = psutil.cpu_percent()

        dd["CPUUsed"] = cpuPercent

        phyMem = psutil.virtual_memory()

        memoryPercent = phyMem.percent

        dd["MemoryUsed"] = memoryPercent

        diskTotal = 0
        diskUse = 0
        diskUsed = 0

        for i in psutil.disk_partitions():
            try:
                tt = dict()
                tt["device"] = i.device
                tt["mount"] = i.mountpoint
                tt["filesystem"] = "Unknown"
                try:
                    tt["filesystem"] = i.fstype
                except:
                    pass
                tt["total_storage"] = psutil.disk_usage(i.mountpoint).total
                tt["storage_used"] = psutil.disk_usage(i.mountpoint).percent
                try:
                    db = ora.connect(self.tns)
                    cr = db.cursor()
                    sql = """
                    insert into om_jkxx_storage
                    values (
                        sys_guid(), 
                        '%s', 
                        to_date('%s', 'yyyy-mm-dd hh24:mi:ss'), 
                        '%s', 
                        '%s', 
                        '%s', 
                        '%s', 
                        %s
                    )
                    """ % (
                        self.alias, 
                        checkTime, 
                        tt["device"], 
                        tt["mount"], 
                        tt["filesystem"], 
                        tt["total_storage"], 
                        tt["storage_used"]
                    )
                    cr.execute(sql)
                    db.commit()
                    if tt["storage_used"] > 90 and tt["storage_used"] <= 95:
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '一般', 
                            '设备%s存储使用率超过90%%', 
                            'SERVER', 
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (
                            tt["device"], 
                            self.alias, 
                            checkTime
                        )
                        cr.execute(sql)
                        db.commit()
                    if tt["storage_used"] > 95 and tt["storage_used"] <= 99:
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '严重', 
                            '设备%s存储使用率超过95%%', 
                            'SERVER', 
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (
                            tt["device"], 
                            self.alias, 
                            checkTime
                        )
                        cr.execute(sql)
                        db.commit()
                    if tt["storage_used"] > 99:
                        sql = """
                        insert into om_warning
                        values (
                            sys_guid(), 
                            '危险', 
                            '设备%s存储使用率超过99%%', 
                            'SERVER', 
                            '%s', 
                            to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                        )
                        """ % (
                            tt["device"], 
                            self.alias, 
                            checkTime
                        )
                        cr.execute(sql)
                        db.commit()
                except Exception as e:
                    print(e)


                diskTotal += psutil.disk_usage(i.mountpoint).total
                diskUse += psutil.disk_usage(i.mountpoint).used
            except:
                pass

        if diskTotal != 0:
            diskUsed = round((diskUse / diskTotal) * 100, 2)

        dd["DiskUsed"] = diskUsed

        print(dd)

        try:
            db = ora.connect(self.tns)
            cr = db.cursor()
            sql = """
            insert into om_jkxx_server
            values (
                sys_guid(), to_date('%s', 'yyyy-mm-dd hh24:mi:ss'), '%s', %s, %s, %s
            )
            """ % (checkTime, self.alias, dd["CPUUsed"], dd["MemoryUsed"], dd["DiskUsed"])
            cr.execute(sql)
            db.commit()
            cr.close()
            db.close()
        except Exception as e:
            print(e)

        if dd["CPUUsed"] > 70 and dd["CPUUsed"] <= 80:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '一般',
                    'CPU使用率超过70%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)
                

        if dd["CPUUsed"] > 80 and dd["CPUUsed"] <= 90:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '严重',
                    'CPU使用率超过80%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)

        if dd["CPUUsed"] > 90:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '危险',
                    'CPU使用率超过90%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)

        if dd["MemoryUsed"] > 70 and dd["MemoryUsed"] <= 80:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '一般',
                    '内存使用率超过70%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)

        if dd["MemoryUsed"] > 80 and dd["MemoryUsed"] <= 90:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '严重',
                    '内存使用率超过80%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)

        if dd["MemoryUsed"] > 90:
            try:
                db = ora.connect(self.tns)
                cr = db.cursor()
                sql = """
                insert into om_warning
                values (
                    sys_guid(), 
                    '危险',
                    '内存使用率超过90%%',
                    'SERVER',
                    '%s', 
                    to_date('%s', 'yyyy-mm-dd hh24:mi:ss')
                )
                """ % (self.alias, checkTime)
                cr.execute(sql)
                db.commit()
                cr.close()
                db.close()
            except Exception as e:
                print(e)

        return dd







class Tomcat(object):
    def __init__(self, ipPort, user, password):
        if "//" not in ipPort:
            ipPort = "http://" + ipPort

        self.ipPort = ipPort
        self.conn = False
        self.user = user
        self.password = password
        self.reqCountB = 0
        self.reqCountA = 0
        self.checkCount = 0

    def probeLogin(self, user, password):
        auth = (user, password)
        url = "%s/probe" % self.ipPort

        try:

            mainGet = rq.get(url, auth=auth)

            resp = mainGet.status_code

            if resp == 200:
                self.conn = True
                return True
            else:
                print("Probe login error. Code: %s\n" % resp)
                self.conn = False
                return False
        except:
            return False

    def reqCheck(self, user, password):
        auth = (user, password)
        url = "%s/probe/index.htm" % self.ipPort

        mainGet = rq.get(url, auth=auth)

        resp = mainGet.status_code

        if resp == 200:
            self.reqCountB = self.reqCountA
            page = self.getHTML(mainGet)
            table = page.split('<table id="app" cellpadding="0" class="genericTbl" cellspacing="0">')[-1]
            table = table.split('</table>')[0]
            body = table.split('<tbody>')[-1]
            body = body.split('</tbody>')[0]

            #appList = list()
            flag = True
            ctRow = 0

            reqCount = 0
            #sessionCount = 0
            while flag:
                ctRow += 1
                row = body.split('</tr>', 1)[0]
                body = body.split('</tr>', 1)[1]
                if '<tr' not in body:
                    flag = False
                
                temp = row.split('</a')[4]
                temp = temp.split('>')[-1].strip()

                reqCount += int(temp)

                #temp = row.split('</a')[5]
                #temp = temp.split('>')[-1].strip()

                #sessionCount += int(temp)

            if self.reqCountB == 0:
                self.reqCountB = reqCount
            self.reqCountA = reqCount

            return self.reqCountA - self.reqCountB

        else:
            print("URL: %s get error. Code: %s\n" % (url, resp))
            return 0

    def jvmCheck(self, user, password):
        auth = (user, password)
        url = "%s/probe/sysinfo.htm" % self.ipPort

        mainGet = rq.get(url, auth=auth)

        resp = mainGet.status_code

        dd = dict()
        dd["FreeMemory"] = 0
        dd["TotalMemory"] = 0
        dd["MaxMemory"] = 0
        dd["MemoryUsed"] = 0

        if resp == 200:
            page = self.getHTML(mainGet)
            body = page.split('<span class="name">Free:</span>&nbsp;<span title="')[-1]
            freeMemory = round(int(body.split('"', 1)[0])/1024/1024/1024, 2)
            body = body.split('"', 1)[1]
            body = body.split('<span class="name">Total:</span>&nbsp;<span title="')[-1]
            totalMemory = round(int(body.split('"', 1)[0])/1024/1024/1024, 2)
            body = body.split('"', 1)[1]
            body = body.split('<span class="name">Max:</span>&nbsp;<span title="')[-1]
            maxMemory = round(int(body.split('"', 1)[0])/1024/1024/1024, 2)
            body = body.split('"', 1)[1]
            memoryUsed = round(((totalMemory - freeMemory) / totalMemory) * 100, 2)
            dd["FreeMemory"] = freeMemory
            dd["TotalMemory"] = totalMemory
            dd["MaxMemory"] = maxMemory
            dd["MemoryUsed"] = memoryUsed
        else:
            print("URL: %s get error. Code: %s\n" % (url, resp))
        
        return dd

    def getHTML(self, mainGet):
        text = str(mainGet.content, encoding='utf-8')
        return text

if __name__ == "__main__":
    prog = Prog()

    print(prog.conf)

    prog.tomcatInit()

    while True:
        print(time.strftime('%Y-%m-%d %X',time.localtime()))
        prog.systemCheck()
        prog.tomcatCheck()
        
        time.sleep(60)

