#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.common import *
import unittest
import time


class TestOrganization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("------------test organization start------------")

    def setUp(self):
        self.rapi1 = RestApi("api/v1/org/cla")
        self.rapi2 = RestApi("api/v1/admin/login")
        self.rapi3 = RestApi("api/v1/admin/org")
        self.rapi4 = RestApi("api/v1/orgs/all")
        data = {
            "account": "administrator",
            "password": "Mugen12#$"
        }
        respon = self.rapi2.post(data=data)
        rsn = json.loads(respon.text)
        self.token = rsn["data"]["token"]

    def test_cla(self):
        data = {
            "name": "testorg",
            "description": "this is my testorg",
            "cla_pass_flag": "data.signed=false",
            "cla_request_type": "GET",
            "cla_sign_url": "https://clasign.osinfra.cn/sign/Z2l0ZWUlMkZvcGVuZXVsZXI=",
            "cla_verify_body": "{}",
            "cla_verify_params": "{\"email\":\"str\"}",
            "cla_verify_url": "https://clasign.osinfra.cn/api/v1/individual-signing/gitee/openeuler",
            "enterprise": "openeuler"
        }
        self.rapi3.header["Authorization"] = "JWT " + self.token
        self.rapi3.header["Content-Type"] = None
        respon = self.rapi3.post2(data=data)
        respon = self.rapi3.get()
        oid = getValbyKeyVal("organization_name", "testorg", "organization_id", respon.text)

        print("验证get获取cla:")
        respon = self.rapi1.get()
        self.assertIn("https://clasign.osinfra.cn/sign/Z2l0ZWUlMkZvcGVuZXVsZXI=", respon.text, "验证get获取cla失败!")

        data = {
            "cla_verify_params": "{\"email\": \"str\"}"
        }
        print("验证post注册组织的cla:")
        respon = RestApi("api/v1/org/" + str(oid) + "/cla").post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "2000","error_msg": "OK"},
        "验证post注册组织的cla失败!")

        print("验证post重复注册组织的cla:")
        respon = RestApi("api/v1/org/" + str(oid) + "/cla").post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code":"5001","error_msg":"relationship has exist"},
        "验证post重复注册组织的cla失败!")

        print("验证post注册不存在组织的cla:")
        respon = RestApi("api/v1/org/" + str(oid + 100000) + "/cla").post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code":"5003","error_msg":"database no find data"},
        "验证post重复注册不存在组织的cla失败!")

        self.rapi2.header["Authorization"] = "JWT " + self.token
        self.rapi2.delete()

    def test_user(self):
        self.rapi3.header["Authorization"] = "JWT " + self.token
        self.rapi3.header["Content-Type"] = None
        respon = self.rapi3.get()
        oid = getValbyKeyVal("organization_name", "testorg", "organization_id", respon.text)
        print("验证get获取当前组织下的user:")
        respon = RestApi("api/v1/org/" + str(oid) + "/users").get()
        self.assertIn('"gitee_name":"Emily_LiuLiu"', respon.text, "验证get获取当前组织下的user失败!")

        self.rapi2.header["Authorization"] = "JWT " + self.token
        self.rapi2.delete()

    def test_group(self):
        self.rapi3.header["Authorization"] = "JWT " + self.token
        self.rapi3.header["Content-Type"] = None
        respon = self.rapi3.get()
        oid = getValbyKeyVal("organization_name", "testorg", "organization_id", respon.text)
        print("验证get获取当前组织下的group:")
        respon = RestApi("api/v1/org/" + str(oid) + "/groups").get()
        self.assertIn('"error_code":"2000","error_msg":"OK"', respon.text, "验证get获取当前组织下的group失败!")

        self.rapi2.header["Authorization"] = "JWT " + self.token
        self.rapi2.delete()

    def test_org(self):
        print("验证get获取当前所有的组织:")
        respon = self.rapi4.get()
        self.assertIn('"name":"testorg"', respon.text, "验证get获取当前所有的组织失败!")
    
    @classmethod
    def tearDownClass(cls) -> None:
        print("------------test organization end--------------")
    
if __name__ == "__main__":
    unittest.main()
