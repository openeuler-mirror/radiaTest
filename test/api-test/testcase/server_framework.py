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
from lib.constant import RET, server_url, gitee_id
from lib.common import UserAuthUnittestTestCase, RestApi


class TestFramework(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test framework interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        self.api_framework = RestApi(
            f"{server_url}/api/v1/framework",
            auth=self.auth
        )
        self.framework_name = "testframework" + self.curtime
        self.framework_url = "https://gitee.com/testframework" + self.curtime

    def test_framework(self):
        logger.info("验证post注册测试框架")
        self.framework_name = "testframework" + self.curtime
        self.framework_url = "https://gitee.com/testframework" + self.curtime
        data = {
            "name": self.framework_name,
            "url": self.framework_url,
            "logs_path": "logs/",
            "adaptive": False,
            "creator_id": gitee_id,
            "permission_type": "public"
        }
        resp = self.api_framework.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post注册测试框架失败!"
        )

        logger.info("验证get条件获取测试框架列表")
        params = {
            "name": self.framework_name,
            "url": self.framework_url
        }
        resp = self.api_framework.get(params=params)
        self.assertIn(
            self.framework_name,
            resp.text,
            "验证get条件获取测试框架列表失败!"
        )
        framework_id = json.loads(resp.text)[0].get("id")
        
        api_framework_item = RestApi(
            f"{server_url}/api/v1/framework/{framework_id}",
            auth=self.auth
        )
        
        logger.info("验证get获取单个测试框架数据")
        resp = api_framework_item.get()
        self.assertIn(
            f'"name":"{self.framework_name}"',
            resp.text,
            "验证get获取单个测试框架数据失败!"
        )

        logger.info("验证删除单个测试框架数据")
        resp = api_framework_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证删除单个测试框架数据失败!"
        )

        api_framework_item.session.close()

    def test_gitrepo(self):
        # enrolling framework for enrolling test git repo
        data = {
            "name": self.framework_name + "tmp",
            "url": self.framework_url + "tmp",
            "logs_path": "logs/",
            "adaptive": False,
            "creator_id": gitee_id,
            "permission_type": "public"
        }
        resp = self.api_framework.post(data=data)
        framework_id = json.loads(resp.text).get("data").get("id")

        api_gitrepo = RestApi(
            f"{server_url}/api/v1/git-repo",
            auth=self.auth
        )

        logger.info("验证post注册脚本代码仓")
        gitrepo_name = "testgitrepo" + self.curtime
        gitrepo_url = "https://gitee.com/testgitrepo" + self.curtime
        data = {
            "name": gitrepo_name,
            "git_url": gitrepo_url,
            "sync_rule": False,
            "framework_id": framework_id,
            "creator_id": gitee_id,
            "permission_type": "person"
        }
        resp = api_gitrepo.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post注册脚本代码仓失败!"
        )

        logger.info("验证get条件获取脚本代码仓列表")
        params = {
            "name": gitrepo_name,
            "url": gitrepo_url
        }
        resp = api_gitrepo.get(params=params)
        self.assertIn(
            gitrepo_name,
            resp.text,
            "验证get条件获取脚本代码仓列表失败!"
        )
        gitrepo_id = json.loads(resp.text)[0].get("id")

        api_gitrepo.session.close()
        
        api_gitrepo_item = RestApi(
            f"{server_url}/api/v1/git-repo/{gitrepo_id}",
            auth=self.auth
        )
        
        logger.info("验证get获取单个脚本代码仓数据")
        resp = api_gitrepo_item.get()
        self.assertIn(
            f'"name":"{gitrepo_name}"',
            resp.text,
            "验证get获取单个脚本代码仓数据失败!"
        )

        logger.info("验证删除单个脚本代码仓数据")
        resp = api_gitrepo_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证删除单个测试框架数据失败!"
        )

        api_gitrepo_item.session.close()
        
        # delete the tmp framework
        api_framework_item = RestApi(
            f"{server_url}/api/v1/framework/{framework_id}"
        )
        api_framework_item.delete()
        api_framework_item.session.close()

    def tearDown(self):
        self.api_framework.session.close()

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test framework interface end--------------")
    
if __name__ == "__main__":
    unittest.main()