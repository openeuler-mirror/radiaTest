#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.common import *
import unittest
import time
import json


class TestProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("------------test product start------------")

    def setUp(self):
        self.rapi = RestApi("api/v1/product")
    
    def test_product(self):
        u"""添加product"""
        data = {
            "description": "openEuler 20.03 LTS SP-add",
            "name": "openEuler",
            "version": "20.03-LTS-SP-add",
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = self.rapi.post(data=data)
        print("验证添加product:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证添加product失败!")

        data = {
            "description": "openEuler 20.03 LTS SP-add",
            "name": "openEuler",
            "version": "20.03-LTS-SP-add",
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = self.rapi.post(data=data)
        print("验证重复添加相同版本的product:")
        self.assertIn("The version of product has existed.", respon.text, "验证重复添加相同版本的product失败!")

        data = {
            "description": "openEuler 20.03 LTS SP17",
            "name": "openEuler",
            "version": "20.03-LTS-SP17",
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "group",
            "group_id": 2
        }

        respon = self.rapi.post(data=data)
        print("验证添加group不存在的product:")
        self.assertIn("The group does not exist or does not belong to current org",respon.text,"验证添加group不存在的product失败!")

        data = {
            "description": "openEuler 20.03 LTS SP17",
            "name": "openEuler",
            "version": "20.03-LTS-SP17",
            "creator_id": 7361816,
            "org_id": 22,
            "permission_type": "public"
        }

        respon = self.rapi.post(data=data)
        print("验证添加org_id不存在的product:")
        self.assertIn("The org is not current login org",respon.text,"验证添加org_id不存在的product失败!")

        respon = self.rapi.get()
        print("验证get获取product:")
        self.assertIn("20.03-LTS-SP-add", respon.text, "验证get获取product失败!")

        pid = getValbyKeyVal("version", "20.03-LTS-SP-add", "id", respon.text)
        respon = RestApi("api/v1/product/" + str(pid)).delete()
    
    def test_product_item(self):
        u"""通过product_id进行获取和删除"""
        data = {
            "description": "openEuler 20.03 LTS SP-add",
            "name": "openEuler",
            "version": "20.03-LTS-SP-add2",
            "creator_id": 7361816,
            "org_id": 2,
            "permission_type": "public"
            }
        respon = self.rapi.post(data=data)

        respon = self.rapi.get()
        p_id = getValbyKeyVal("version", "20.03-LTS-SP-add2", "id", respon.text)

        data = {
            "description": "openEuler 20.03 LTS SP-edit",
            "name": "openEuler",
            "version": "20.03-LTS-SP-edit",
            "id": p_id
            }

        self.rapi2 = RestApi("api/v1/product/" + str(p_id))
        respon = self.rapi2.put(data=data)
        print("验证put通过product_id接口修改product:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证put通过product_id接口修改product失败!")
        
        respon = self.rapi2.get()
        print("验证通过product/product_id接口get获取product:")
        self.assertIn("20.03-LTS-SP-edit", respon.text, "验证get获取product失败!")

        respon = self.rapi2.delete()
        print("验证通过product/product_id接口delete删除product:")
        self.assertDictEqual(json.loads(respon.text), 
        {"error_code": "2000","error_msg": "Request processed successfully."},
        "验证delete删除produc失败!")
    
    @classmethod
    def tearDownClass(cls) -> None:
        print("------------test product end--------------")

if __name__ == "__main__":
    unittest.main()
