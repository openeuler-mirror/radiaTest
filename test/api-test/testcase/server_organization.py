#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import unittest

from lib import logger
from lib.constant import RET, server_url
from lib.common import RestApi, AdminAuthUnittestTestCase, get_val_by_key_val


class TestOrganization(AdminAuthUnittestTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        logger.info("------------test organization start------------")
        super().setUpClass()

    def setUp(self):
        self.api_org_cla = RestApi(
            f"{server_url}/api/v1/org/cla",
            auth=self.auth
        )
        self.api_admin_org = RestApi(
            f"{server_url}/api/v1/admin/org"
        )
        self.api_orgs_all = RestApi(
            f"{server_url}/api/v1/orgs/all"
        )

    def test_cla(self):
        logger.info("验证创建组织")
        data = {
            "name": "testorg",
            "description": "this is my testorg",
            "cla_pass_flag": "data.signed=true",
            "cla_request_type": "GET",
            "cla_sign_url": "https://clasign.osinfra.cn/sign/testorg=",
            "cla_verify_body": "{}",
            "cla_verify_params": "{\"email\":\"str\"}",
            "cla_verify_url": "https://clasign.osinfra.cn/api/v1/individual-signing/gitee/openeuler",
            "enterprise": 123456,
            "oauth_client_id": "testorg",
            "oauth_client_secret": "testorg",
            "oauth_scope": "user_info,enterprise_info,issues",
            "enterprise_json_url": "https://www.baidu.com"
        }
        respon = self.api_admin_org.post2(data=data)
        self.assertDictEqual(
            json.loads(respon.text),
            {
                "error_code": RET.OK,
                "error_msg": "OK",
            }
        )

        respon = self.api_admin_org.get() 
        oid = get_val_by_key_val("organization_name", "testorg", "organization_id", respon.text) 
        
        logger.info("验证get获取组织的cla签署地址")
        respon = self.api_org_cla.get()
        self.assertIn(
            "https://clasign.osinfra.cn/sign/testorg=", 
            respon.text, 
            "验证get获取组织的cla签署地址失败!"
        )

        logger.info("验证post验证用户的cla邮箱")
        data = {
            "cla_verify_params": "{\"email\": \"ethanzhang55@outlook.com\"}"
        }
        respon = RestApi(
            f"{server_url}/api/v1/org/" + str(oid) + "/cla"
        ).post(data=data)
        self.assertDictEqual(
            json.loads(respon.text),
            {
                "error_code": RET.OK,
                "error_msg": "OK"
            },
            "验证post验证用户的cla邮箱失败!"
        )

        logger.info("验证post注册不存在组织的cla")
        respon = RestApi(f"{server_url}/api/v1/org/" + str(oid + 100000) + "/cla").post(data=data)
        self.assertDictEqual(
            json.loads(respon.text),
            {
                "error_code": RET.NO_DATA_ERR,
                "error_msg": "database no find data"
            },
            "验证post重复注册不存在组织的cla失败!"
        )

    def test_user(self):
        logger.info("验证get获取指定组织下的所有成员")
        respon = self.api_admin_org.get()
        oid = get_val_by_key_val("organization_name", "testorg", "organization_id", respon.text)
        respon = RestApi(
            f"{server_url}/api/v1/org/" + str(oid) + "/users"
        ).get()
        self.assertIn(
            f'"error_code":"{RET.OK}","error_msg":"OK"', 
            respon.text,
            "验证get获取指定组织下的所有成员失败!"
        )

    def test_group(self):
        logger.info("验证get获取当前组织下的用户组列表")
        respon = self.api_admin_org.get()
        oid = get_val_by_key_val("organization_name", "testorg", "organization_id", respon.text)
        respon = RestApi(
            f"{server_url}/api/v1/org/" + str(oid) + "/groups"
        ).get()
        self.assertIn(
            f'"error_code":"{RET.OK}","error_msg":"OK"', 
            respon.text, 
            "验证get获取当前组织下的用户组列表失败!"
        )


    def test_org(self):
        logger.info("验证get获取当前所有的组织")
        respon = self.api_orgs_all.get()
        self.assertIn(
            '"name":"testorg"', 
            respon.text, 
            "验证get获取当前所有的组织失败!"
        )
    
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        logger.info("------------test organization end--------------")


if __name__ == "__main__":
    unittest.main()
