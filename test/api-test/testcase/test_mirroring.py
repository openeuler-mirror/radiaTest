#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.common import *
import unittest
import time

class TestMirroring(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("------------test mirroring start------------")
        rapi = RestApi("api/v1/product")
        data = {
            "description": "openEuler 20.03 LTS SP2-milestone",
            "name": "openEuler",
            "version": "20.03-LTS-SP2-milestone",
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = rapi.post(data=data)
        respon = rapi.get()
        pid = getValbyKeyVal("version", "20.03-LTS-SP2-milestone", "id", respon.text)
        rapi = RestApi("api/v2/milestone")
        data = {
            "end_time": "2022-04-17 00:00:00",
            "name": "openEuler-20.03-LTS-SP2-milestone-round-test",
            "product": "openEuler",
            "product_id": pid,
            "start_time": "2022-04-16 00:00:00",
            "type": "round", 
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = rapi.post(data=data)

        data = {
            "end_time": "2022-04-17 00:00:00",
            "name": "openEuler-20.03-LTS-SP2-milestone-update-test",
            "product": "openEuler",
            "product_id": pid,
            "start_time": "2022-04-16 00:00:00",
            "type": "update", 
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = rapi.post(data=data)
    
    def setUp(self):
        self.rapi = RestApi("api/v2/milestone?page_size=200")
        respon = self.rapi.get()
        self.mid = getValbyKeyVal2("name", "openEuler-20.03-LTS-SP2-milestone-round-test", "id", respon.text)

    def test_imirroring_err(self):
        respon = self.rapi.get()
        self.mid = getValbyKeyVal2("name", "openEuler-20.03-LTS-SP2-milestone-update-test", "id", respon.text)
        self.rapi = RestApi("api/v1/imirroring")
        data = {
            "milestone_id": self.mid,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.rapi.post(data=data)
        print("验证milestone.type='update',不支持imirroring:")
        self.assertIn("Only the release version and iterative version can be bound to the iso image.", 
            respon.text,
            "验证milestone.type='update',不支持imirroring:失败!")
        
    def test_imirroring_err2(self):
        self.rapi = RestApi("api/v1/imirroring")
        url_tmp = "http://www.test.com/a.iso"
        data = {
            "milestone_id": self.mid,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": url_tmp
        }
        respon = self.rapi.post(data=data)
        print("验证post创建imirroring，url不通:")
        self.assertIn("url:%s is not available." % url_tmp, 
            respon.text,
            "验证post创建imirroring，url不通失败!")
        
    def test_imirroring_err3(self):
        self.rapi = RestApi("api/v1/imirroring")
        data = {
            "milestone_id": str(self.mid + 10000),
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
        }
        respon = self.rapi.post(data=data)
        print("验证post创建imirroring，milestone_id不存在:")
        self.assertIn("The milestone does not exist.", 
            respon.text,
            "验证post创建imirroring，milestone_id不存在失败!")

    def test_imirroring(self):
        self.rapi = RestApi("api/v1/imirroring")
        print(self.mid)
        data = {
            "milestone_id": self.mid,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.rapi.post(data=data)
        print("验证添加arm架构的imirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加imirroring失败!")

        data = {
            "milestone_id": self.mid,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.rapi.post(data=data)
        print("验证添加imirroring，同一个里程碑，arm架构的只能添加一个:")
        self.assertIn("The url of aarch64 iso image already exists under the milestone.",
            respon.text, 
            "验证添加imirroring失败!")
        
        data = {
            "milestone_id": self.mid,
            "frame": "x86_64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/EFI/BOOT/grubx64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler_x86-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/x86_64/openEuler-20.03-LTS-SP2-x86_64-dvd.iso"
            }
        respon = self.rapi.post(data=data)
        print("验证添加x86架构imirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加x86架构imirroring失败!")

        data = {
            "milestone_id": self.mid,
            "frame": "x86_64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/EFI/BOOT/grubx64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler_x86-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/x86_64/openEuler-20.03-LTS-SP2-x86_64-dvd.iso"
            }
        respon = self.rapi.post(data=data)

        print("验证添加imirroring，同一个里程碑，x86架构的只能添加一个:")
        self.assertIn("The url of x86_64 iso image already exists under the milestone.",
            respon.text, 
            "验证添加imirroring失败!")
        
        print("验证preciseget获取imirroring:")
        respon = RestApi("api/v1/imirroring/preciseget?milestone_id=" + str(self.mid)).get()
        self.assertIn("openEuler-20.03-LTS-SP2/OS/x86_64/",
            respon.text, 
            "验证precisegetget获取imirroring失败!")
        self.assertIn("openEuler-20.03-LTS-SP2/OS/aarch64/",
            respon.text, 
            "验证preciseget获取imirroring失败!")

        data = {
            "milestone_id": self.mid,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.rapi.post(data=data)
        respon = RestApi("api/v1/imirroring/preciseget?milestone_id=" + str(self.mid)).get()
        imid1 = getValbyKeyVal("ks", "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg", "id", respon.text)
        imid2 = getValbyKeyVal("ks", "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler_x86-2.cfg", "id", respon.text)

        data = {
            "milestone_id": self.mid,
            "id": imid1,
            "frame": "aarch64",
            "efi": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": "http://139.9.114.65:9400/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/test",
            "url": "http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        self.rapi2 = RestApi("api/v1/imirroring/" + str(imid1))
        respon =self.rapi2.put(data=data)
        print("验证put通过i_mirroring_id修改imirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证put通过i_mirroring_id修改imirroring失败!")
         
        print("验证get通过i_mirroring_id获取imirroring:")
        respon = self.rapi2.get()
        self.assertIn("openEuler-20.03-LTS-SP2/OS/aarch64/test",
            respon.text, 
            "验证get通过i_mirroring_id获取imirroring失败!")

        print("验证delete通过i_mirroring_id删除imirroring:")
        self.rapi2_1 = RestApi("api/v1/imirroring/" + str(imid2))
        respon = self.rapi2.delete()
        respon = self.rapi2_1.delete()
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证delete通过i_mirroring_id删除imirroring失败!")

    def test_qmirroring_err(self):
        respon = self.rapi.get()
        self.mid = getValbyKeyVal2("name", "openEuler-20.03-LTS-SP2-milestone-update-test", "id", respon.text)
        self.rapi = RestApi("api/v1/qmirroring")
        data = {
            "frame": "x86_64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.rapi.post(data=data)
        print("验证milestone.type='update',不支持qmirroring:")
        self.assertIn("Only the release version and iterative version can be bound to the iso image.", 
            respon.text,
            "验证milestone.type='update',不支持qmirroring:失败!")
    
    def test_qmirroring_err2(self):
        self.rapi = RestApi("api/v1/qmirroring")
        url_tmp = "http://www.test.com/a.qcow2"
        data = {
            "frame": "x86_64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": url_tmp,
            "user": "root"
        }
        respon = self.rapi.post(data=data)
        print("验证post创建qmirroring，url不通:")
        self.assertIn("url:%s is not available." % url_tmp, 
            respon.text,
            "验证post创建qmirroring，url不通失败!")
    
    def test_qmirroring_err3(self):
        self.rapi = RestApi("api/v1/qmirroring")
        data = {
            "milestone_id": str(self.mid + 10000),
            "frame": "x86_64",
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.rapi.post(data=data)
        print("验证post创建qmirroring，milestone_id不存在:")
        self.assertIn("The milestone does not exist.", 
            respon.text,
            "验证post创建qmirroring，milestone_id不存在失败!")
    
    def test_qmirroring(self):
        self.rapi = RestApi("api/v1/qmirroring")
        data = {
            "frame": "x86_64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.rapi.post(data=data)
        print("验证添加x86_64架构的qmirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加qmirroring失败!")

        data = {
            "frame": "x86_64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
            }
        respon = self.rapi.post(data=data)
        print("验证添加qmirroring，同一个里程碑，x86架构的只能添加一个:")
        self.assertIn("The url of x86_64 qcow image already exists under the milestone.",
            respon.text, 
            "验证添加qmirroring失败!")
        
        data = {
            "frame": "aarch64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.rapi.post(data=data)
        print("验证添加aarch64架构qmirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "q")

        data = {
            "frame": "aarch64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.rapi.post(data=data)

        print("验证添加qmirroring，同一个里程碑，aarch64架构的只能添加一个:")
        self.assertIn("The url of aarch64 qcow image already exists under the milestone.",
            respon.text, 
            "验证添加qmirroring失败!")
        
        print("验证preciseget获取qmirroring:")
        respon = RestApi("api/v1/qmirroring/preciseget?milestone_id=" + str(self.mid)).get()
        self.assertIn("/openEuler/20.03-LTS-SP2/x86_64/",
            respon.text, 
            "验证precisegetget获取qmirroring失败!")
        self.assertIn("/openEuler/20.03-LTS-SP2/aarch64/",
            respon.text, 
            "验证preciseget获取qmirroring失败!")      
        
        data = {
            "frame": "aarch64",
            "milestone_id": self.mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.rapi.post(data=data)
        respon = RestApi("api/v1/qmirroring/preciseget?milestone_id=" + str(self.mid)).get()
        qmid1 = getValbyKeyVal("url", "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2", "id", respon.text)
        qmid2 = getValbyKeyVal("url", "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2", "id", respon.text)

        data = {
            "frame": "aarch64",
            "milestone_id": self.mid,
            "id": qmid1,
            "password": "openEuler34#$",
            "port": 22,
            "url": "http://139.9.114.65:9400/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        self.rapi2 = RestApi("api/v1/qmirroring/" + str(qmid1))
        self.rapi2_1 = RestApi("api/v1/qmirroring/" + str(qmid2))
        respon = self.rapi2.put(data=data)
        print("验证put通过q_mirroring_id修改qmirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证put通过q_mirroring_id修改qmirroring失败!")
        

        respon = self.rapi2.get()
        self.assertIn("/openEuler/20.03-LTS-SP2/aarch64/",
            respon.text, 
            "验证get通过q_mirroring_id获取qmirroring失败!")

        respon = self.rapi2.delete()
        respon = self.rapi2_1.delete()
        print("验证delete通过q_mirroring_id删除qmirroring:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证delete通过q_mirroring_id删除qmirroring失败!")

    def test_repo(self):
        self.rapi = RestApi("api/v1/repo")
        data = {
            "content": "[OS]\nname=aarch64\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "aarch64",
            "milestone_id": self.mid
        }
        respon = self.rapi.post(data=data)
        print("验证添加arm架构的repo:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加arm架构repo失败!")

        data = {
            "content": "[OS]\nname=aarch64\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "aarch64",
            "milestone_id": self.mid
        }
        respon = self.rapi.post(data=data)
        print("验证添加repo，同一个里程碑，aarch64架构的只能添加一个:")
        self.assertIn("The repo address is already registered.",
            respon.text, 
            "验证添加repo，同一个里程碑，aarch64架构的只能添加一个失败!")
        
        
        data = {
            "content": "[OS]\nname=x86_64\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "x86_64",
            "milestone_id": self.mid
        }
        respon = self.rapi.post(data=data)
        print("验证添加x86_64架构的repo:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加x86_64架构repo失败!")

        data = {
            "content": "[OS]\nname=x86_64\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "x86_64",
            "milestone_id": self.mid
        }
        respon = self.rapi.post(data=data)
        print("验证添加repo，同一个里程碑，x86_64架构的只能添加一个:")
        self.assertIn("The repo address is already registered.",
            respon.text, 
            "验证添加repo，同一个里程碑，x86_64架构的只能添加一个失败!")
        

        print("验证get获取repo:")
        respon = self.rapi.get()
        self.assertIn("x86_64",
            respon.text, 
            "验证get获取repo失败!")
        self.assertIn("aarch64",
            respon.text, 
            "验证get获取repo失败!")
        #通过frame获取的话，只要repo中有frame为x86_64和aarch64的都会被获取到，但是通过content获取有点问题
        rid1 = getValbyKeyVal("frame", "x86_64", "id", respon.text)
        rid2 = getValbyKeyVal("frame", "aarch64", "id", respon.text)
        data = {
            "content": "[OS]\nname=x86_64\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n",
            "frame": "x86_64",
            "milestone_id": self.mid,
            "id": rid1
        }
        respon = self.rapi.put(data=data)
        print("验证put修改repo:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证put修改repo失败!")

        data = {
            "content": "[OS]\nname=OS\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "aarch64",
            "milestone_id": self.mid,
            "id": rid1
        }
        respon = self.rapi.put(data=data)
        print("验证put修改repo不能覆盖其他架构已存在的repo:")
        self.assertIn("The repo address is already registered.", 
            respon.text,
            "验证put修改repo不能覆盖其他架构已存在的repo失败!")
        
        data = {
            "id": [rid1, rid2]
        }
        respon = self.rapi.delete(data=data)
        print("验证delete删除repo:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证delete删除repo失败!")

    def test_repo_err(self):
        self.rapi = RestApi("api/v1/repo")
        data = {
            "content": "[OS]\nname=OS\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[everything]\nname=everything\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/everything/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL]\nname=EPOL\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/EPOL/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n\n[debuginfo]\nname=debuginfo\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/debuginfo/$basearch/RPM-GPG-KEY-openEuler\n\n[source]\nname=source\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/source/RPM-GPG-KEY-openEuler\n\n[update]\nname=update\nbaseurl=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/update/$basearch/\nenabled=1\ngpgcheck=1\ngpgkey=http://139.9.114.65:9400/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/$basearch/RPM-GPG-KEY-openEuler\n",
            "frame": "aarch64",
            "milestone_id": str(self.mid + 100),
        }
        respon = self.rapi.post(data=data)
        print("验证post创建repo，milestone_id不存在:")
        self.assertIn("The milestone does not exist.", 
            respon.text,
            "验证post创建repo，milestone_id不存在失败!")
    
        
    @classmethod
    def tearDownClass(cls) -> None:
        respon = RestApi("api/v2/milestone").get()
        mid1 = getValbyKeyVal2("name", "openEuler-20.03-LTS-SP2-milestone-round-test", "id", respon.text)
        mid2 = getValbyKeyVal2("name", "openEuler-20.03-LTS-SP2-milestone-update-test", "id", respon.text)
        respon = RestApi("api/v2/milestone/" + str(mid1)).delete()
        respon = RestApi("api/v2/milestone/" + str(mid2)).delete()

        rapi = RestApi("api/v1/product")
        respon = rapi.get()
        pid = getValbyKeyVal("version", "20.03-LTS-SP2-milestone", "id", respon.text)
        data = {
            "id": [pid]
        }
        respon = RestApi("api/v1/product" + str(pid)).delete(data=data)
        print("------------test mirroring end--------------")
    
if __name__ == "__main__":
    unittest.main()
