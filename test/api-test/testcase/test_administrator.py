#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime
import os
import sys
import unittest
import pytz
sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])

from lib import logger


from lib.constant import account, password, RET
from lib.common import AuthUnittestTestCase, RestApi, get_val_by_key_val


class TestAdministrator(AuthUnittestTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("------------test Administrator start------------")
        super().setUpClass()

    def setUp(self):
        self.api_login = RestApi("/api/v1/admin/login")
        self.api_org = RestApi("/api/v1/admin/org", auth=TestAdministrator.auth)

    def test_admin_login(self):
        logger.info("验证登录Administrator")
        data = {
            "account": account,
            "password": password
        }
        resp = self.api_login.post(data=data)
        self.assertIn("token", resp.text, "验证登录Administrator失败!")

        logger.info("验证登录Administrator时密码错误")
        data = {
            "account": account,
            "password": f"wrong{password}"
        }
        resp = self.api_login.post(data=data)
        self.assertDictEqual(
            json.loads(resp.text),
            {
                "error_code": RET.VERIFY_ERR,
                "error_msg": "password error"
            },
            "验证登录Administrator时密码错误失败!"
        )

        logger.info("验证登录Administrator时用户名错误")
        data = {
            "account": f"wrong{account}",
            "password": password
        }
        resp = self.api_login.post(data=data)
        self.assertDictEqual(
            json.loads(resp.text),
            {
                "error_code": RET.NO_DATA_ERR,
                "error_msg": "admin no find"
            },
            "验证登录Administrator时用户名错误失败!"
        )

        self.api_login.session.close()

    def test_admin_org(self):
        org_name = f"testOrganization{datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y%m%d%H%M%S')}"

        logger.info("验证Administrator登录后post注册新组织")
        data = {
            "name": org_name,
            "description": "organization for testing"
        }
        resp = self.api_org.post2(data=data)
        self.assertDictEqual(
            json.loads(resp.text),
            {
                "error_code": RET.OK, 
                "error_msg": "OK"
            },
            "验证Administrator登录后post注册新组织失败!"
        )

        logger.info("验证Administrator登录后post注册已存在的组织")
        resp = self.api_org.post2(data=data)
        self.assertDictEqual(
            json.loads(resp.text),
            {
                "error_code": RET.DATA_EXIST_ERR, 
                "error_msg": "organizations name exist"
            },
            "验证Administrator登录后post注册已存在的组织失败!"
        )
        
        logger.info("验证Administrator登录后get组织信息")
        resp = self.api_org.get()
        self.assertIn(
            org_name,
            resp.text,
            "注册的组织查询失败，验证Administrator登录后get组织信息失败!"
        )

        logger.info("验证Administrator登陆后通过org_id修改组织信息")
        oid = get_val_by_key_val(
            "organization_name", 
            org_name, 
            "organization_id", 
            resp.text,
        )
        data = {
            "name": f"{org_name}-edit",
            "description": f"editting testOrganization{org_name}"
        }
        api_org_correct_item = RestApi(f"/api/v1/admin/org/{oid}", auth=TestAdministrator.auth)
        resp = api_org_correct_item.put2(data=data)
        self.assertDictEqual(
            json.loads(resp.text), 
            {
                "error_code": RET.OK,
                "error_msg": "OK"
            },
            "验证Administrator登录后put通过org_id修改组织信息失败!"
        )

        logger.info("验证Administrator登录后put通过不存在的org_id修改组织信息")
        wrong_oid = oid + 1000000
        api_org_wrong_item = RestApi(f"/api/v1/admin/org/{wrong_oid}", auth=TestAdministrator.auth)
        respon = api_org_wrong_item.put2(data=data)
        
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.NO_DATA_ERR,
                "error_msg": "the organization does not exist"
            },
            "验证Administrator登录后put通过不存在的org_id修改组织信息失败!"
        )
        
        logger.info("验证Administrator登录后put通过org_id删除组织")
        data = {
            "is_delete": "true"
        }
        respon = api_org_correct_item.put2(data=data)
        self.assertDictEqual(
            json.loads(respon.text), 
            {
                "error_code": RET.OK,
                "error_msg": "OK"
            },
            "验证Administrator登录后put通过org_id删除组织失败!"
        )

        api_org_correct_item.session.close()
        api_org_wrong_item.session.close()
        self.api_org.session.close()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        logger.info("------------test Administrator end--------------")
    
if __name__ == "__main__":
    unittest.main()
