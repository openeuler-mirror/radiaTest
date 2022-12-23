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
# 用例管理(Testcase-BaselineTemplate)相关接口的UT
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


class TestBaseLineTemplate(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test baselinetemplate interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        self.api_baselinetemplate = RestApi(
            f"{server_url}/api/v1/baseline-template",
            auth=self.auth
        )
        self.api_base_node = RestApi(
            f"{server_url}/api/v1/base-node/",
            auth=self.auth
        )
        self.pre_api_baseline = RestApi(
            f"{server_url}/api/v1/baseline",
            auth=self.auth
        )
        self.baselinetemplate_name = "test_baselinetemplate" + self.curtime
        self.base_node_name = "test_base_node" + self.curtime
        self.baseline_name = "test_baseline" + self.curtime

        res = self.create_pre_data()
        self.pre_baselinetemplate_id = res.get("pre_baseline_template_id")
        self.pre_base_node_id = res.get("base_node_id")
        self.pre_baseline_id = res.get("baseline_id")
        self.pre_case_node_id = res.get("case_node_id") 
        self.root_base_node_id = res.get("root_base_node_id")
        self.pre_api_baselinetemplate_item = RestApi(
            f"{server_url}/api/v1/baseline-template/{self.pre_baselinetemplate_id}",
            auth=self.auth
        )
        self.pre_api_case_node_item = RestApi(
            f"{server_url}/api/v1/case-node/{self.pre_case_node_id}",
            auth=self.auth
        )
        self.pre_api_base_node_item = RestApi(
            f"{server_url}/api/v1/base-node/{self.pre_base_node_id}",
            auth=self.auth
        )
        self.pre_api_baseline_item = RestApi(
            f"{server_url}/api/v1/baseline/{self.pre_baseline_id}",
            auth=self.auth
        )

    def create_pre_data(self):
        logger.info("验证post创建基线模板")
        return_data = dict()
        data = {
            "title": "pre_" + self.baselinetemplate_name,
            "type": "group",
            "group_id":1,
            "openable":True
        }
        resp = self.api_baselinetemplate.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}","error_msg":"Request processed successfully."',
            resp.text,
            "验证post创建基线模板失败!"
        )
        root_base_node_id = json.loads(resp.text).get("data").get("id") 
        logger.info(root_base_node_id)  

        api_base_node_item = RestApi(
            f"{server_url}/api/v1/base-node/{root_base_node_id}",
            auth=self.auth
        )
        resp = api_base_node_item.get2()
        pre_baseline_template_id = json.loads(resp.text).get("data").get("baseline_template_id") 
        logger.info(pre_baseline_template_id)  

        logger.info("验证post创建基线模板节点")
        data = {
            "title": "pre_" + self.base_node_name,
            "is_root": False,
            "parent_id": root_base_node_id,
        }

        self.api_base_node_new = RestApi(
            f"{server_url}/api/v1/baseline-template/{pre_baseline_template_id}/base-node",
            auth=self.auth
        )
        resp = self.api_base_node_new.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线模板节点失败!"
        )
        base_node_id = json.loads(resp.text).get("data")
        logger.info(base_node_id)  


        logger.info("验证post创建基线")
        data = {
            "title": "pre_" + self.baseline_name,
            "type": "baseline",
            "group_id": 1,
            "milestone_id": 1
        }
        resp = self.pre_api_baseline.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线模板失败!"
        )
        baseline_id = json.loads(resp.text).get("data").get("baseline_id")  
        case_node_id = json.loads(resp.text).get("data").get("case_node_id")  
        return_data.update({
            "pre_baseline_template_id": pre_baseline_template_id,
            "base_node_id": base_node_id,
            "baseline_id": baseline_id,
            "case_node_id": case_node_id,
            "root_base_node_id": root_base_node_id,
        })

        return return_data


    def test_baselinetemplate(self):
        logger.info("验证post创建基线模板")
        data = {
            "title": self.baselinetemplate_name,
            "type": "group",
            "group_id":1,
            "openable":True
        }
        resp = self.api_baselinetemplate.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线模板失败!"
        )
        basenode_id = json.loads(resp.text).get("data").get("id")
        
        
        api_base_node_item = RestApi(
            f"{server_url}/api/v1/base-node/{basenode_id}",
            auth=self.auth
        )
        resp = api_base_node_item.get2()
        baseline_template_id = json.loads(resp.text).get("data").get("baseline_template_id") 
        logger.info(baseline_template_id)  


        logger.info("验证get获取基线模板")
        api_baselinetemplate_item = RestApi(
            f"{server_url}/api/v1/baseline-template/{baseline_template_id}",
            auth=self.auth
        )
        params = {
            "openable" : True,
        }
        resp = api_baselinetemplate_item.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取基线模板失败!"
        )


        logger.info("验证get获取指定基线模板")
        resp = api_baselinetemplate_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定基线模板失败!"
        )


        logger.info("验证put编辑指定基线模板")
        data = {
            "name": "updated_" + self.baselinetemplate_name
        }
        resp = api_baselinetemplate_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定基线模板失败!"
        )

        logger.info("验证post继承指定基线模板")

        api_baselinetemplate_inherit = RestApi(
            f"{server_url}/api/v1/baseline-template/{baseline_template_id}/inherit/{self.pre_baselinetemplate_id}",
            auth=self.auth
        )        
        resp = api_baselinetemplate_inherit.post()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post继承指定基线模板失败!"
        )


        logger.info("验证post应用指定基线")
        api_baselinetemplate_item_apply = RestApi(
            f"{server_url}/api/v1/case-node/{self.pre_case_node_id}\
                /apply/baseline-template/{self.pre_baselinetemplate_id}",
            auth=self.auth
        )
        data = {}
        resp = api_baselinetemplate_item_apply.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post应用指定基线失败!"
        )


        logger.info("验证delete清空指定基线模板")
        api_baselinetemplate_item_clean = RestApi(
            f"{server_url}/api/v1/baseline-template/{baseline_template_id}/clean",
            auth=self.auth
        )
        data = {}
        resp = api_baselinetemplate_item_clean.delete(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete清空指定基线模板失败!"
        )


        logger.info("验证delete指定基线模板")
        resp = api_baselinetemplate_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定基线模板失败!"
        )

        api_baselinetemplate_item.session.close()
        api_baselinetemplate_inherit.session.close()
        api_baselinetemplate_item_apply.session.close()
        api_baselinetemplate_item_clean.session.close()


    def test_base_node(self):
        logger.info("验证post创建基线模板节点")
        data = {
            "title": self.base_node_name,
            "is_root": False,
            "parent_id": self.root_base_node_id,
        }

        resp = self.api_base_node_new.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post创建基线模板节点失败!"
        )
        base_node_id = json.loads(resp.text).get("data")


        logger.info("验证get获取基线模板节点")
        params = {
            "is_root" : False,
        }
        resp = self.api_base_node_new.get2(params=params)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取基线模板节点失败!"
        )


        logger.info("验证get获取指定基线模板节点")
        api_base_node_item = RestApi(
            f"{server_url}/api/v1/base-node/{base_node_id}",
            auth=self.auth
        )
        resp = api_base_node_item.get2()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证get获取指定基线模板节点失败!"
        )


        logger.info("验证put编辑指定基线模板节点")
        data = {
            "name": "updated_" + self.base_node_name
        }
        resp = api_base_node_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证put编辑指定基线模板节点失败!"
        )



        logger.info("验证delete指定基线模板节点")
        resp = api_base_node_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定基线模板节点失败!"
        )

        api_base_node_item.session.close()



    def tearDown(self):
        logger.info("验证delete指定基线模板")
        resp = self.pre_api_baselinetemplate_item.delete(data={})
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定基线模板失败!"
        )


        logger.info("验证delete指定基线")
        resp = self.pre_api_baseline_item.delete()
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证delete指定基线模板!"
        )

        self.api_baselinetemplate.session.close()
        self.api_base_node.session.close()
        self.pre_api_baseline_item.session.close()
        self.pre_api_baselinetemplate_item.session.close()
        self.pre_api_case_node_item.session.close()
        self.pre_api_base_node_item.session.close()


    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test baselinetemplate interface end--------------")
    
if __name__ == "__main__":
    unittest.main()
