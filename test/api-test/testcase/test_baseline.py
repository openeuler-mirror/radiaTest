# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)相关接口的UT
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


class TestBaseline(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test baseline interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        self.api_baseline = RestApi(
            f"{server_url}/api/v1/baseline",
            auth=self.auth
        )
        self.api_case_node = RestApi(
            f"{server_url}/api/v1/case-node",
            auth=self.auth
        )

        self.api_suite = RestApi(
            f"{server_url}/api/v1/suite",
            auth=self.auth
        )
        self.api_case = RestApi(
            f"{server_url}/api/v1/case",
            auth=self.auth
        )
        self.pre_api_baseline = RestApi(
            f"{server_url}/api/v1/baseline",
            auth=self.auth
        ) 
        self.baseline_name = "test_baseline" + self.curtime
        self.case_node_name = "test_case_node" + self.curtime
        self.suite_name = "test_suite" + self.curtime
        self.case_name = "test_case" + self.curtime
        self.suite_document_name = "test_suite_document" + self.curtime


        res = self.create_pre_data()
        self.pre_baseline_id = res.get("baseline_id")
        self.root_baseline_case_node_id = res.get("case_node_id")
        self.pre_suite_id = res.get("suite_id")
        self.pre_case_node_id = res.get("case_node_suite_id")
        self.root_case_node = res.get("root_case_node")
        
        self.pre_api_baseline_item = RestApi(
            f"{server_url}/api/v1/baseline/{self.pre_baseline_id}",
            auth=self.auth
        ) 
        self.pre_api_case_node_baseline_item = RestApi(
            f"{server_url}/api/v1/case-node/{self.root_baseline_case_node_id}",
            auth=self.auth
        )
        self.pre_api_case_node_item = RestApi(
            f"{server_url}/api/v1/case-node/{self.pre_case_node_id}",
            auth=self.auth
        )
        self.pre_api_suite_item = RestApi(
            f"{server_url}/api/v1/suite/{self.pre_suite_id}",
            auth=self.auth
        )

    def create_pre_data(self):
        logger.info("验证post创建基线")
        return_data = dict()
        data = {
            "title": "pre_" + self.baseline_name,
            "type": "baseline",
            "group_id": 1,
            "milestone_id": 1
        }
        resp = self.api_baseline.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线失败!"
        )
        baseline_id = json.loads(resp.text).get("data").get("baseline_id")  
        case_node_id = json.loads(resp.text).get("data").get("case_node_id")
        logger.info(baseline_id)  
        logger.info(case_node_id)  
    

        params = {
            "title": "用例集",
            "group": 1
        }
        resp = self.api_case_node.get2(params=params)
        root_case_node = json.loads(resp.text).get("data")[0].get("id") 
        logger.info(root_case_node)  
        logger.info("验证post创建suite以及case-node节点")
        data = {
            "name": "pre_" + self.suite_name,
            "group_id": 1,
            "parent_id": root_case_node
        }
        resp = self.api_suite.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建suite以及case-node节点失败!"
        )
        suite_id = json.loads(resp.text).get("data").get("suite_id")
        case_node_suite_id = json.loads(resp.text).get("data").get("case_node_id")
        return_data.update({
            "baseline_id": baseline_id,
            "case_node_id": case_node_id,
            "suite_id": suite_id,
            "case_node_suite_id": case_node_suite_id,
            "root_case_node": root_case_node,
        })

        return return_data


    def test_baseline(self):
        logger.info("验证post创建基线")
        data = {
            "title": self.baseline_name,
            "type": "baseline",
            "group_id": 1,
            "milestone_id": 1
        }
        resp = self.api_baseline.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线失败!"
        )
        baseline_id = json.loads(resp.text).get("data").get("baseline_id")
        case_node_id = json.loads(resp.text).get("data").get("case_node_id") 


        logger.info("验证get获取基线")
        params = {
            "id" : baseline_id,
        }
        resp = self.api_baseline.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取基线失败!"
        )


    def test_case_node(self):
        logger.info("验证post创建case-node节点")
        data = {
            "baseline_id": self.pre_baseline_id,
            "title": self.case_node_name,
            "type":"directory",
            "group_id":1
        }
        resp = self.api_case_node.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建case-node节点失败!"
        )
        case_node_id = json.loads(resp.text).get("data")


        logger.info("验证get获取case-node节点")
        api_case_node_item = RestApi(
            f"{server_url}/api/v1/case-node/{case_node_id}",
            auth=self.auth
        )
        params = {
            "id" : case_node_id,
        }
        resp = self.api_case_node.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取case-node节点失败!"
        )


        logger.info("验证get获取指定case-node节点")
        resp = api_case_node_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定case-node节点失败!"
        )


        logger.info("验证put编辑指定case-node节点")
        data = {
            "title": "updated_" + self.case_node_name
        }
        resp = api_case_node_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定case-node节点失败!"
        )

        logger.info("验证delete指定case-node节点")
        resp = api_case_node_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定case-node节点失败!"
        )

        api_case_node_item.session.close()


    def test_suite(self):
        logger.info("验证post创建suite以及case-node节点")
        data = {
            "name": self.suite_name,
            "group_id": 1,
            "parent_id": self.root_case_node
        }
        resp = self.api_suite.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建suite以及case-node节点失败!"
        )
        suite_id = json.loads(resp.text).get("data").get("suite_id")
        case_node_id = json.loads(resp.text).get("data").get("case_node_id")


        logger.info("验证get获取suite节点")
        params = {
            "id" : suite_id,
        }
        resp = self.api_suite.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取suite节点失败!"
        )


        logger.info("验证get获取指定suite节点详情")
        api_suite_item = RestApi(
            f"{server_url}/api/v1/suite/{suite_id}",
            auth=self.auth
        )
        resp = api_suite_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定suite节点详情失败!"
        )


        logger.info("验证put编辑指定suite以及case-node节点")
        data = {
            "name": "updated_" + self.suite_name
        }
        resp = api_suite_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定suite以及case-node节点失败!"
        )


        logger.info("验证delete指定suite以及case-node节点")
        resp = api_suite_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定指定suite以及case-node节点失败!"
        )

        api_suite_item.session.close()


    def test_suite_document(self):
        logger.info("验证post创建suite下的document")
        api_document = RestApi(
            f"{server_url}/api/v1/suite/{self.pre_suite_id}/document",
            auth=self.auth
        )
        data = {
            "title": self.suite_document_name,
            "url": "www.hello.com",
        }
        resp = api_document.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建suite下的document失败!"
        )
        document_id = json.loads(resp.text).get("data").get("id")


        logger.info("验证get获取suite下的document")
        api_document_item = RestApi(
            f"{server_url}/api/v1/suite-document/{document_id}",
            auth=self.auth
        )
        resp = api_document_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取suite下的document!"
        )


        logger.info("验证get获取指定suite下的document")
        resp = api_document_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定suite下的document失败!"
        )


        logger.info("验证put编辑指定suite下的document")
        data = {
            "name": "updated_" + self.suite_name
        }
        resp = api_document_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定suite下的document失败!"
        )


        logger.info("验证delete指定suite下的document")
        resp = api_document_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定指定suite下的document失败!"
        )

        api_document.session.close()
        api_document_item.session.close()


    def test_case(self):
        logger.info("验证post创建case以及case-node节点")
        data = {
            "suite": "pre_" + self.suite_name,
            "name": self.case_name,
            "test_level": "单元测试",
            "test_type": "功能测试",
            "machine_type": "kvm",
            "owner": "MDS_ZHR",
            "automatic": True,
            "add_disk": "",
            "description": self.case_name,
            "preset": self.case_name,
            "steps": self.case_name,
            "expection": self.case_name,
            "group_id": 1
        }
        resp = self.api_case.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建case以及case-node节点失败!"
        )
        case_id = json.loads(resp.text).get("data").get("case_id")
        case_node_id = json.loads(resp.text).get("data").get("case_node_id")


        logger.info("验证get获取case节点")
        params = {
            "id" : case_id,
        }
        resp = self.api_case.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取case节点失败!"
        )


        logger.info("验证get获取指定case节点详情")
        api_case_item = RestApi(
            f"{server_url}/api/v1/case/{case_id}",
            auth=self.auth
        )
        resp = api_case_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定case节点详情失败!"
        )


        logger.info("验证put编辑指定case以及case-node节点")
        data = {
            "name": "updated_" + self.case_name
        }
        resp = api_case_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定case以及case-node节点失败!"
        )


        logger.info("验证delete指定case以及case-node节点")
        resp = api_case_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定指定case以及case-node节点失败!"
        )

        api_case_item.session.close()


    def test_baseline_case_node(self):
        logger.info("验证get获取group下的所有casenode节点")
        
        api_baseline_resource = RestApi(
            f"{server_url}/api/v1/case-node/{self.root_baseline_case_node_id}/resource",
            auth=self.auth
        )
        resp = api_baseline_resource.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取group下的所有casenode节点失败!"
        )

        api_baseline_resource.session.close()


    def test_caseset_case_node(self):
        logger.info("验证get获取group下的所有casenode节点")
        api_resource_case_node = RestApi(
            f"{server_url}/api/v1/case-node/{self.root_case_node}/resource",
            auth=self.auth
        )
        resp = api_resource_case_node.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取group下的所有casenode节点失败!"
        )
        api_resource_case_node.session.close()


    def test_org_case_node(self):
        logger.info("验证get获取org下的所有casenode节点节点")
        org_id = 1
        api_org_resource = RestApi(
            f"{server_url}/api/v1/org/{org_id}/resource",
            auth=self.auth
        )
        params = {
            "commit_type" : "week",
        }
        resp = api_org_resource.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取org下的所有casenode节点失败!"
        )

        api_org_resource.session.close()


    def test_group_case_node(self):
        logger.info("验证get获取group下的所有casenode节点")
        group_id = 1
        api_group_resource = RestApi(
            f"{server_url}/api/v1/group/{group_id}/resource",
            auth=self.auth
        )
        params = {
            "commit_type" : "week",
        }
        resp = api_group_resource.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取group下的所有casenode节点失败!"
        )


    def tearDown(self):
        logger.info("验证delete指定基线")
        resp = self.pre_api_baseline_item.delete(data={})
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定基线失败!"
        )
        
        
        logger.info("验证delete指定suite的case_node")
        resp = self.pre_api_suite_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定suite的case_node!"
        )


        self.api_baseline.session.close()
        self.api_case_node.session.close()
        self.pre_api_baseline.session.close()
        self.pre_api_baseline_item.session.close()
        self.pre_api_case_node_item.session.close()
        self.pre_api_case_node_item.session.close()
        self.pre_api_case_node_baseline_item.session.close()


    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test baseline interface end--------------")
    
if __name__ == "__main__":
    unittest.main()

