#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.common import *
import unittest
import time
import requests


class TestAdministrator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("------------test Administrator start------------")

    def setUp(self):
        self.rapi1 = RestApi("api/v1/admin/register")
        self.rapi2 = RestApi("api/v1/admin/login")
        self.rapi3 = RestApi("api/v1/admin/org")
        self.rapi4 = RestApi("api/v1/logout")

    def test_admin_register(self):
        data = {
            "account": "mytest",
            "password": "openEuler12#$",
            "password2": "openEuler12#$"
        }
        print("验证注册Administrator:")
        respon = self.rapi1.post(data=data)
        self.assertIn("token", respon.text, "验证注册Administrator失败!")

        print("验证注册已经存在的Administrator:")
        respon = self.rapi1.post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "5001","error_msg": "data has exist / foreign key is bond"},
        "验证注册已经存在的Administrator失败!")

    def test_admin_login(self):
        data = {
            "account": "mytest2",
            "password": "openEuler12#$",
            "password2": "openEuler12#$"
        }
        print("验证注册Administrator:")
        respon = self.rapi1.post(data=data)

        data = {
            "account": "mytest2",
            "password": "openEuler12#$"
        }
        print("验证登录Administrator:")
        respon = self.rapi2.post(data=data)
        self.assertIn("token", respon.text, "验证登录Administrator失败!")

        data = {
            "account": "mytest2",
            "password": "openEuler12#$!"
        }
        print("验证登录Administrator时密码错误:")
        respon = self.rapi2.post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "4001","error_msg": "password error"},
        "验证登录Administrator时密码错误失败!")

        data = {
            "account": "mytest2t",
            "password": "openEuler12#$"
        }
        print("验证登录Administrator时用户名错误:")
        respon = self.rapi2.post(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "5003","error_msg": "admin no find"},
        "验证登录Administrator时用户名错误失败!")


    def test_admin_org(self):
        data = {
            "account": "administrator",
            "password": "Mugen12#$"
        }
        respon = self.rapi2.post(data=data)
        rsn = json.loads(respon.text)
        token = rsn["data"]["token"]

        data = {
            "name": "testopenEuler",
            "description": "this is my test"
        }
        self.rapi3.header["Authorization"] = "JWT " + token
        self.rapi3.header["Content-Type"] = None

        print("验证Administrator登录后post注册新组织:")
        respon = self.rapi3.post2(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "2000","error_msg": "OK"},
        "验证Administrator登录后post注册新组织失败!")

        print("验证Administrator登录后post注册已存在的组织:")
        respon = self.rapi3.post2(data=data)
        self.assertDictEqual(json.loads(respon.text),
        {"error_code": "5001", "error_msg": "organizations name exist"},
        "验证Administrator登录后postd注册已存在的组织失败!")

        print("验证Administrator登录后get组织信息:")
        respon = self.rapi3.get()
        self.assertIn("testopenEuler",respon.text,"验证Administrator登录后get组织信息失败!")
        
        # 退出当前用户
        self.rapi4.header["Authorization"] = "JWT " + token
        self.rapi4.delete()

    def test_admin_org_item(self):
        data = {
            "account": "administrator",
            "password": "Mugen12#$"
        }
        respon = self.rapi2.post(data=data)
        rsn = json.loads(respon.text)
        token = rsn["data"]["token"]

        data = {
            "name": "testopenEuler-put",
            "description": "this is my test-put"
        }
        self.rapi3.header["Authorization"] = "JWT " + token
        self.rapi3.header["Content-Type"] = None
        respon = self.rapi3.post2(data=data)
        respon = self.rapi3.get()
        oid = getValbyKeyVal("organization_name", "testopenEuler-put", "organization_id", respon.text)

        data = {
            "name": "testopenEuler-put-edit",
            "description": "this is my test-edit"
        }
        self.rapi3_1 = RestApi("api/v1/admin/org/" + str(oid))
        self.rapi3_1.header["Authorization"] = "JWT " + token 
        self.rapi3_1.header["Content-Type"] = None
        respon = self.rapi3_1.put2(data=data)
        print("验证Administrator登录后put通过org_id修改组织信息:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "OK"},
        "验证Administrator登录后put通过org_id修改组织信息失败!")

        self.rapi3_2 = RestApi("api/v1/admin/org/" + str(oid + 10000))
        self.rapi3_2.header["Authorization"] = "JWT " + token
        self.rapi3_2.header["Content-Type"] = None
        respon = self.rapi3_2.put2(data=data)
        print("验证Administrator登录后put通过不存在的org_id修改组织信息:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "5003","error_msg": "no find organization"},
        "验证Administrator登录后put通过不存在的org_id修改组织信息失败!")
        
        data = {
            "is_delete": "true"
        }
        respon = self.rapi3_1.put2(data=data)
        print("验证Administrator登录后put通过org_id删除组织:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "OK"},
        "验证Administrator登录后put通过org_id删除组织失败!")

         # 退出当前用户
        self.rapi4.header["Authorization"] = "JWT " + token
        self.rapi4.delete()

    @classmethod
    def tearDownClass(cls) -> None:
        print("------------test Administrator end--------------")
    
if __name__ == "__main__":
    unittest.main()
