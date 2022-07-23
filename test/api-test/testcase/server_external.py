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
from lib.constant import RET, server_url, cacert_path
from lib.common import UserAuthUnittestTestCase, RestApi


class TestExternal(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test external interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")

    def test_update_task_event(self):
        api_update_task_event = RestApi(
            f"{server_url}/api/v1/openeuler/task/update",
        )

        logger.info("验证post触发openEuler的update版本测试验证")
        data = {
            "product": "openEuler",
            "version": "20.03-LTS-SP3",
            "pkgs": ["jq", "abrt", "kernel", "dnf"],
            "base_update_url": "http://121.36.84.172/repo.openeuler.org/openEuler-20.03-LTS-SP3/update_20220713/",
            "epol_update_url": "http://121.36.84.172/repo.openeuler.org/openEuler-20.03-LTS-SP3/EPOL/update_20220713/main/"
        }
        resp = api_update_task_event.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post触发openEuler的update版本测试验证失败!"
        )

        api_update_task_event.session.close()
    
    def test_login_org_list(self):
        api_login_org_list = RestApi(
            f"{server_url}/api/v1/login/org/list",
        )

        logger.info("验证get获取平台已注册的组织名")
        resp = self.api_login_org_list.get()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取平台已注册的组织名失败"
        )

        api_login_org_list.session.close()
    
    def test_vmachine_exist(self):
        vmachine_domain = "test_domain"

        logger.info("验证get查询虚拟机是否存在于数据库")
        rapi = RestApi(
            f"{server_url}/api/v1/vmachine/check-exist?name={vmachine_domain}",
        )
        resp = rapi.get()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get查询虚拟机是否存在于数据库失败"
        )

        rapi.session.close()
    
    def test_cacert(self):
        api_cacert = RestApi(
            f"{server_url}/api/v1/ca-cert",
            auth=self.auth
        )

        logger.info("验证get获取服务端ca根证书")
        with open(cacert_path, "r") as f:
            cacert_content = f.read()
            resp = api_cacert.get()
            self.assertEqual(
                cacert_content,
                json.loads(resp.text),
                "验证get获取服务端ca根证书失败!"
            )

        api_cacert.session.close()
       
    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test external interface end--------------")
    
if __name__ == "__main__":
    unittest.main()