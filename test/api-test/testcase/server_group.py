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
from lib.constant import RET, server_url, user_token_2, gitee_id_2, gitee_id
from lib.common import UserAuthUnittestTestCase, RestApi


class TestGroup(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test group interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        self.api_group = RestApi(
            f"{server_url}/api/v1/groups",
            auth=self.auth
        )
        self.group_name = "test_group" + self.curtime

    def test_group(self):
        logger.info("验证post创建用户组")
        data = {
            "name": self.group_name,
        }
        resp = self.api_group.post2(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建用户组失败!"
        )
        group_id = json.loads(resp.text).get("data").get("id")

        logger.info("验证get获取当前用户所属的用户组")
        params = {
            "page_num": 1,
            "page_size": 999
        }
        resp = self.api_group.get(params=params)
        self.assertIn(
            f'"name":"{self.group_name}"',
            resp.text,
            "验证get获取当前用户所属的用户组失败!"
        )

        api_group_item = RestApi(
            f"{server_url}/api/v1/groups/{group_id}",
            auth=self.auth
        )

        logger.info("验证put编辑指定用户组")
        data = {
            "name": "updated_" + self.group_name
        }
        resp = api_group_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定用户组失败!"
        )

        logger.info("验证delete解散指定用户组")
        resp = api_group_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete解散指定用户组失败!"
        )

        api_group_item.session.close()

    def test_user(self):
        # enrolling tmp group for testing interface
        data = {
            "name": self.group_name + "tmp",
        }
        resp = self.api_group.post2(data=data)
        group_id = json.loads(resp.text).get("data").get("id")

        api_group_user = RestApi(
            f"{server_url}/api/v1/groups/{group_id}/users",
            auth=f"JWT {user_token_2}"
        )

        logger.info("验证post提交用户加入指定用户组申请")
        data = {
            "gitee_ids": [gitee_id_2]
        }
        resp = api_group_user.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post提交用户加入指定用户组申请失败!"
        )

        api_group_user.session.close()

        api_group_user = RestApi(
            f"{server_url}/api/v1/groups/{group_id}/users",
            auth=self.auth
        )

        logger.info("验证get获取指定用户组下的用户列表")
        resp = api_group_user.get()
        self.assertIn(
            gitee_id,
            resp.text,
            "验证get获取指定用户组下的用户列表失败!"
        )

        logger.info("验证put编辑指定用户组下的用户的角色")
        data = {
            "gitee_ids": [gitee_id],
            "role_type": "admin"
        }
        resp = api_group_user.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定用户组下的用户的状态失败!"
        )

        api_group_user.session.close()

    def tearDown(self):
        self.api_group.session.close()

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test framework interface end--------------")
    
if __name__ == "__main__":
    unittest.main()