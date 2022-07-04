#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import unittest
from datetime import datetime
import os
import sys
import pytz
sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])

from lib import logger
from lib.constant import gitee_id, RET, repo_url
from lib.common import AuthUnittestTestCase, RestApi, get_val_by_key_val, get_val_by_key_val2


class TestMirroring(AuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test mirroring start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
        rapi = RestApi("/api/v1/product", auth=cls.auth)
        data = {
            "description": "milestone openEuler 20.03 LTS SP2 for test mirroring",
            "name": "openEuler",
            "version": f"20.03-LTS-SP2-{cls.curtime}",
            "creator_id": gitee_id,
            # 后续不需要传org_id, 为public类型
            "org_id": 1,
            "permission_type": "public"
            }
        rapi.post(data=data)
        respon = rapi.get()
        cls.pid = get_val_by_key_val(
            "version", 
            f"20.03-LTS-SP2-{cls.curtime}", 
            "id", 
            respon.text
        )
        rapi.session.close()

        rapi = RestApi("/api/v2/milestone", auth=cls.auth)
        data = {
            "end_time": "2022-04-17 00:00:00",
            "name": f"20.03-LTS-SP2 round {cls.curtime}",
            "product_id": cls.pid,
            "start_time": "2022-04-16 00:00:00",
            "type": "round", 
            "creator_id": gitee_id,
            # 后续不需要传org_id, 为public类型
            "org_id": 1,
            "permission_type": "public"
            }
        respon = rapi.post(data=data)

        data = {
            "end_time": "2022-04-17 00:00:00",
            "name": f"20.03-LTS-SP2 update{cls.curtime}",
            "product_id": cls.pid,
            "start_time": "2022-04-16 00:00:00",
            "type": "update", 
            "creator_id": gitee_id,
            # 后续不需要传org_id, 为public类型
            "org_id": 1,
            "permission_type": "public"
            }
        respon = rapi.post(data=data)
        rapi.session.close()
    
        rapi = RestApi("/api/v2/milestone?page_size=200", auth=TestMirroring.auth)
        respon = rapi.get()
        cls.round_mid = get_val_by_key_val2(
            "name", 
            f"20.03-LTS-SP2 round {TestMirroring.curtime}", 
            "id", 
            respon.text
        )
        cls.update_mid = get_val_by_key_val2(
            "name", 
            f"20.03-LTS-SP2 update{TestMirroring.curtime}", 
            "id", 
            respon.text
        )
        rapi.session.close()

    def setUp(self):
        self.api_imirroring = RestApi("/api/v1/imirroring", auth=TestMirroring.auth)
        self.api_qmirroring = RestApi("/api/v1/qmirroring", auth=TestMirroring.auth)
        self.api_repo = RestApi("/api/v1/repo", auth=TestMirroring.auth)

    def test_imirroring_err(self):
        logger.info("验证milestone.type='update',不支持imirroring")
        data = {
            "milestone_id": TestMirroring.update_mid,
            "frame": "aarch64",
            "efi": f"http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": f"http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": f"http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": f"http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)

        self.assertIn(
            "Only the release version and iterative version can be bound to the iso image.", 
            respon.text,
            "验证milestone.type='update',不支持imirroring:失败!"
        )
        
    def test_imirroring_err2(self):
        logger.info("验证post创建imirroring，url不通")
        url_tmp = "http://www.test.com/a.iso"
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "aarch64",
            "efi": f"http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            "ks": f"http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            "location": f"http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            "url": url_tmp
        }
        respon = self.api_imirroring.post(data=data)
        self.assertIn(
            "url:%s is not available." % url_tmp, 
            respon.text,
            "验证post创建imirroring，url不通失败!"
        )
        
    def test_imirroring_err3(self):
        logger.info("验证post创建imirroring，milestone_id不存在")
        data = {
            "milestone_id": str(TestMirroring.round_mid + 1000000),
            "frame": "aarch64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
        }
        respon = self.api_imirroring.post(data=data)
        
        self.assertIn(
            "The milestone does not exist.", 
            respon.text,
            "验证post创建imirroring，milestone_id不存在失败!"
        )

    def test_imirroring(self):
        logger.info("验证添加arm架构的imirroring")
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "aarch64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加imirroring失败!"
        )

        logger.info("验证添加imirroring，同一个里程碑，arm架构的只能添加一个")
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "aarch64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)
        
        self.assertIn(
            "The url of aarch64 iso image already exists under the milestone.",
            respon.text, 
            "验证添加imirroring失败!"
        )
        
        logger.info("验证添加x86架构imirroring")
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "x86_64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/EFI/BOOT/grubx64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler_x86-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/x86_64/openEuler-20.03-LTS-SP2-x86_64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {  
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加x86架构imirroring失败!"
        )

        logger.info("验证添加imirroring，同一个里程碑，x86架构的只能添加一个")
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "x86_64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/EFI/BOOT/grubx64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler_x86-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/x86_64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/x86_64/openEuler-20.03-LTS-SP2-x86_64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)

        self.assertIn(
            "The url of x86_64 iso image already exists under the milestone.",
            respon.text, 
            "验证添加imirroring失败!"
        )
        
        logger.info("验证preciseget获取imirroring")
        respon = RestApi(
            "/api/v1/imirroring/preciseget?milestone_id=" + str(TestMirroring.round_mid), 
            auth=TestMirroring.auth
        ).get()
        self.assertIn(
            "openEuler-20.03-LTS-SP2/OS/x86_64/",
            respon.text, 
            "验证precisegetget获取imirroring失败!"
        )
        self.assertIn(
            "openEuler-20.03-LTS-SP2/OS/aarch64/",
            respon.text, 
            "验证preciseget获取imirroring失败!"
        )

        logger.info("验证put通过i_mirroring_id修改imirroring")
        data = {
            "milestone_id": TestMirroring.round_mid,
            "frame": "aarch64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        respon = self.api_imirroring.post(data=data)
        respon = RestApi(
            "/api/v1/imirroring/preciseget?milestone_id=" + str(TestMirroring.round_mid), 
            auth=TestMirroring.auth
        ).get()
        imid1 = get_val_by_key_val(
            "ks", 
            f"http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg", 
            "id", 
            respon.text
        )

        data = {
            "milestone_id": TestMirroring.round_mid,
            "id": imid1,
            "frame": "aarch64",
            f"efi": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/EFI/BOOT/grubaa64.efi",
            f"ks": "http://{repo_url}/ks/GUI_20.03_LTS_SP2/openeuler-2.cfg",
            f"location": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/OS/aarch64/test",
            f"url": "http://{repo_url}/repo_list/official.repo/openEuler-20.03-LTS-SP2/ISO/aarch64/openEuler-20.03-LTS-SP2-aarch64-dvd.iso"
            }
        api_imirroring_item_1 = RestApi("/api/v1/imirroring/" + str(imid1), auth=TestMirroring.auth)
        respon = api_imirroring_item_1.put(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证put通过i_mirroring_id修改imirroring失败!"
        )
         
        logger.info("验证get通过i_mirroring_id获取imirroring")
        respon = api_imirroring_item_1.get()
        self.assertIn(
            "openEuler-20.03-LTS-SP2/OS/aarch64/test",
            respon.text, 
            "验证get通过i_mirroring_id获取imirroring失败!"
        )

        logger.info("验证delete通过i_mirroring_id删除imirroring")
        respon = api_imirroring_item_1.delete()
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证delete通过i_mirroring_id删除imirroring失败!"
        )

        api_imirroring_item_1.session.close()

    def test_qmirroring_err(self):
        logger.info("验证milestone.type='update',不支持qmirroring")
        data = {
            "frame": "x86_64",
            "milestone_id": TestMirroring.update_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.api_qmirroring.post(data=data)
        self.assertIn(
            "Only the release version and iterative version can be bound to the iso image.", 
            respon.text,
            "验证milestone.type='update',不支持qmirroring:失败!"
        )
    
    def test_qmirroring_err2(self):
        logger.info("验证post创建qmirroring，url不通")
        url_tmp = "http://www.test.com/a.qcow2"
        data = {
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            "url": url_tmp,
            "user": "root"
        }
        respon = self.api_qmirroring.post(data=data)
        
        self.assertIn(
            "url:%s is not available." % url_tmp, 
            respon.text,
            "验证post创建qmirroring，url不通失败!"
        )
    
    def test_qmirroring_err3(self):
        logger.info("验证post创建qmirroring，milestone_id不存在:")
        data = {
            "milestone_id": str(TestMirroring.round_mid + 1000000),
            "frame": "x86_64",
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.api_qmirroring.post(data=data)
        self.assertIn(
            "The milestone does not exist.", 
            respon.text,
            "验证post创建qmirroring，milestone_id不存在失败!"
        )
    
    def test_qmirroring(self):
        logger.info("验证添加x86_64架构的qmirroring:")
        data = {
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
        }
        respon = self.api_qmirroring.post(data=data)
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加qmirroring失败!"
        )

        logger.info("验证添加qmirroring，同一个里程碑，x86架构的只能添加一个")
        data = {
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2",
            "user": "root"
            }
        respon = self.api_qmirroring.post(data=data)
        
        self.assertIn(
            "The url of x86_64 qcow image already exists under the milestone.",
            respon.text, 
            "验证添加x86_64架构qmirroring失败!"
        )
        
        logger.info("验证添加aarch64架构qmirroring")
        data = {
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.api_qmirroring.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加aarch64架构qmirroring失败"
        )

        logger.info("验证添加qmirroring，同一个里程碑，aarch64架构的只能添加一个")
        data = {
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.api_qmirroring.post(data=data)

        self.assertIn(
            "The url of aarch64 qcow image already exists under the milestone.",
            respon.text, 
            "验证添加qmirroring失败!"
        )
        
        logger.info("验证preciseget获取qmirroring:")
        respon = RestApi(
            "/api/v1/qmirroring/preciseget?milestone_id=" + str(TestMirroring.round_mid), 
            auth=TestMirroring.auth
        ).get()
        self.assertIn(
            "/openEuler/20.03-LTS-SP2/x86_64/",
            respon.text, 
            "验证precisegetget获取qmirroring失败!"
        )
        self.assertIn(
            "/openEuler/20.03-LTS-SP2/aarch64/",
            respon.text, 
            "验证preciseget获取qmirroring失败!"
        )      
        
        logger.info("验证put通过q_mirroring_id修改qmirroring")
        data = {
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid,
            "password": "openEuler12#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        respon = self.api_qmirroring.post(data=data)
        respon = RestApi(
            "/api/v1/qmirroring/preciseget?milestone_id=" + str(TestMirroring.round_mid), 
            auth=TestMirroring.auth
        ).get()
        qmid1 = get_val_by_key_val(
            "url", 
            "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2", 
            "id", 
            respon.text
        )
        qmid2 = get_val_by_key_val(
            "url", 
            f"http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/x86_64/openEuler-20.03-LTS-SP2.x86_64.qcow2", 
            "id", 
            respon.text
        )

        data = {
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid,
            "id": qmid1,
            "password": "openEuler34#$",
            "port": 22,
            f"url": "http://{repo_url}/repo_list/mugen.mirror/official/openEuler/20.03-LTS-SP2/aarch64/openEuler-20.03-LTS-SP2.aarch64.qcow2",
            "user": "root"
            }
        api_qmirroring_item_1 = RestApi("/api/v1/qmirroring/" + str(qmid1), auth=TestMirroring.auth)
        respon = self.api_qmirroring.put(data=data)
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证put通过q_mirroring_id修改qmirroring失败!"
        )
        

        respon = api_qmirroring_item_1.get()
        self.assertIn(
            "/openEuler/20.03-LTS-SP2/aarch64/",
            respon.text, 
            "验证get通过q_mirroring_id获取qmirroring失败!"
        )

        logger.info("验证delete通过q_mirroring_id删除qmirroring:")
        respon = api_qmirroring_item_1.delete()

        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证delete通过q_mirroring_id删除qmirroring失败!"
        )

        api_qmirroring_item_1.session.close()

    def test_repo(self):
        logger.info("验证添加aarch64架构的repo到round里程碑")
        data = {
            f"content": "[OS]\nname=aarch64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=0\n",
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid
        }
        respon = self.api_repo.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加aarch64架构repo到round里程碑失败!"
        )

        logger.info("验证添加aarch64架构的repo到update里程碑")
        data = {
            f"content": "[OS]\nname=aarch64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=0\n",
            "frame": "aarch64",
            "milestone_id": TestMirroring.update_mid
        }
        respon = self.api_repo.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加aarch64架构repo到update里程碑失败!"
        )

        logger.info("验证添加repo，同一个里程碑，aarch64架构的只能添加一个")
        data = {
            f"content": "[OS]\nname=aarch64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=0\n",
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid
        }
        respon = self.api_repo.post(data=data)
        
        self.assertIn(
            "The repo address is already registered.",
            respon.text, 
            "验证添加repo，同一个里程碑，aarch64架构的只能添加一个失败!"
        )
        
        logger.info("验证添加x86_64架构的repo到round里程碑")
        data = {
            f"content": "[OS]\nname=x86_64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=0\n",
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid
        }
        respon = self.api_repo.post(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证添加x86_64架构repo失败!"
        )

        logger.info("验证添加repo，同一个里程碑，x86_64架构的只能添加一个")
        data = {
            f"content": "[OS]\nname=x86_64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=0",
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid
        }
        respon = self.api_repo.post(data=data)
        
        self.assertIn(
            "The repo address is already registered.",
            respon.text, 
            "验证添加repo，同一个里程碑，x86_64架构的只能添加一个失败!"
        )
        

        logger.info("验证get获取repo")
        respon = self.api_repo.get()
        self.assertIn(
            "x86_64",
            respon.text, 
            "验证get获取repo失败!"
        )
        self.assertIn(
            "aarch64",
            respon.text, 
            "验证get获取repo失败!"
        )

        logger.info("验证put修改repo")
        #通过frame获取的话，只要repo中有frame为x86_64和aarch64的都会被获取到，但是通过content获取有点问题
        rid1 = get_val_by_key_val("frame", "x86_64", "id", respon.text)
        rid2 = get_val_by_key_val("frame", "aarch64", "id", respon.text)
        data = {
            f"content": "[OS]\nname=x86_64\nbaseurl=http://{repo_url}/repo_list\nenabled=1\ngpgcheck=1\n",
            "frame": "x86_64",
            "milestone_id": TestMirroring.round_mid,
            "id": rid1
        }
        respon = self.api_repo.put(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证put修改repo失败!"
        )

        logger.info("验证put修改repo不能覆盖其他架构已存在的repo")
        data = {
            f"content": "[OS]\nname=OS\nbaseurl=http://{repo_url}/repo_list/official.repo",
            "frame": "aarch64",
            "milestone_id": TestMirroring.round_mid,
            "id": rid1
        }
        respon = self.api_repo.put(data=data)
        
        self.assertIn(
            "The repo address is already registered.", 
            respon.text,
            "验证put修改repo不能覆盖其他架构已存在的repo失败!"
        )
        
        logger.info("验证delete删除repo")
        data = {
            "id": [rid1, rid2]
        }
        respon = self.api_repo.delete(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "Request processed successfully."
            },
            "验证delete删除repo失败!"
        )


    def test_repo_err(self):
        logger.info("验证post创建repo，milestone_id不存在")
        data = {
            f"content": "[OS]\nname=OS\nbaseurl=http://{repo_url}/repo_list/official.repo",
            "frame": "aarch64",
            "milestone_id": str(TestMirroring.round_mid + 1000000),
        }
        respon = self.api_repo.post(data=data)
        
        self.assertIn(
            "The milestone does not exist.", 
            respon.text,
            "验证post创建repo，milestone_id不存在失败!"
        )

    def tearDown(self) -> None:
        self.api_imirroring.session.close()
        self.api_qmirroring.session.close()
        self.api_repo.session.close()
        
    @classmethod
    def tearDownClass(cls) -> None:
        RestApi("/api/v2/milestone/" + str(cls.round_mid), auth=TestMirroring.auth).delete()
        RestApi("/api/v2/milestone/" + str(cls.update_mid), auth=TestMirroring.auth).delete()
        RestApi("/api/v1/product" + str(cls.pid), auth=TestMirroring.auth).delete()
        super().tearDownClass()
        logger.info("------------test mirroring end--------------")
    
if __name__ == "__main__":
    unittest.main()
