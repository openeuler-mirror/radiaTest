# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : 董霖峰
# email : 1063183942@qq.com
# Date : 2023/01/16 05:24:55
# License : Mulan PSL v2
#####################################
# 手工测试任务(ManualJob)相关接口的UT
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import json
import unittest
from datetime import datetime, timedelta
import os
import sys
import pytz

sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])

from lib import logger
from lib.constant import gitee_id
from lib.common import UserAuthUnittestTestCase, RestApi
from lib.constant import RET, server_url
# server_url = https://192.168.200.200:8080
# user_token = eyJhbGciOiJIUzUxMiIsImlhdCI6MTY3MzQ0MTY2OSwiZXhwIjoxNjczODAxNjY5fQ.qVte2KlKj3Dri06MHsw+5bgQ34uARzMhOV3Tl6jkHGUFobmV8g6mBlF3gFXcnGTjrN0YwhPyjR1c0YXCSIYRumDDdOFCJTIzu1SKABICY18=.ZkN3yWqCkPkNDx6FKqxVNmFK6bJuMxpmHTeJ8Ipt3OFyMEA0AXmFCXcmMBmLmKM_du-XLu1Tprbk1TRH4Ddr-Q
# gitee_id = 10973848


class TestManualJob(UserAuthUnittestTestCase):
    DATETIME_CURTIME = datetime.now(pytz.timezone('Asia/Shanghai'))
    CURTIME = DATETIME_CURTIME.strftime("%Y%m%d%H%M%S")
    SUITE_NAME = "test_suite_" + CURTIME
    CASE_NAME = "test_case_" + CURTIME
    MILESTONE_NAME = "test_milestone_" + CURTIME
    CASE_DESCRIPTION = "test_case_description_" + CURTIME
    CASE_PRESET = "test_case_preset_" + CURTIME
    CASE_EXPECTION = "test_case_expection_" + CURTIME
    MANUAL_JOB_NAME = ["test_manual_job_0_" + CURTIME, "test_manual_job_1_" + CURTIME]  # 测试中创建的2个manual_job的名字

    CASE_ID: int
    MILESTONE_ID: int
    MANUAL_JOB_ID: list[int] = [None, None]  # 测试中创建的2个manual_job的id

    TOTAL_STEP = 3  # 总步骤数
    STEP_OPERATION = ["", "1. test_case_step\n", "2. test_case_step\n",
                      "3. test_case_step\n"]  # (2个manual_job所属的同一个)case的操作步骤文本
    LOG_CONTENT = ["", "1. test_log_content\n", "2. test_log_content\n",
                   "3. test_log_content\n"]  # 初次录入的(2个manual_job同样的)日志内容
    MODIFY_STEP: int  # 测试中被修改的日志的步骤序号
    DELETE_STEP: int  # 测试中被删除的日志的步骤序号
    MODIFY_LOG_CONTENT = "修改过的日志"  # 测试中修改后的日志内容

    @classmethod
    def _get_manual_job_event_url(cls, status: int = None) -> str:
        if status is not None:
            return f"/api/v1/manual-job?status={status}"
        return "/api/v1/manual-job"

    @classmethod
    def _get_manual_job_submit_event_url(cls, manual_job_id: int) -> str:
        return f"/api/v1/manual-job/{manual_job_id}/submit"

    @classmethod
    def _get_manual_job_log_event_url(cls, manual_job_id: int) -> str:
        return f"/api/v1/manual-job/log/{manual_job_id}"

    @classmethod
    def _get_manual_job_delete_event_url(cls, manual_job_id: int) -> str:
        return f"/api/v1/manual-job/{manual_job_id}"

    @classmethod
    def _get_manual_job_log_query_event_url(cls, manual_job_id: int, step_num: int) -> str:
        return f"/api/v1/manual-job/{manual_job_id}/step/{step_num}"

    @classmethod
    def setUpClass(cls):
        logger.info("------------test manual_job interface start------------")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test framework interface end--------------")

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def _parse_response_json_to_dict(
        cls,
        response_text: str,
        parse_fail_message: str = "返回体格式不对, 无法按json解析"
    ) -> dict:
        try:
            response_dict = json.loads(response_text)
        except Exception as e:
            logger.error(parse_fail_message)
        return response_dict

    def test01_preparations(self):
        """
            准备工作: 创建suite, 创建case, 创建milestone.
        """
        # 创建suite
        logger.info("test01_准备工作")
        logger.info("创建suite")
        api_create_suite = RestApi(server_url + "/api/v1/suite", auth=self.auth)  # 在这里面已经打开session了
        data_create_suite = {
            "name": TestManualJob.SUITE_NAME,
            "machine_num": 1,
            "machine_type": "kvm",
            "add_network_interface": None,
            "add_disk": None,
            "remark": None,
            "deleted": False,
            "owner": None,
            "git_repo_id": None,
            "permission_type": "person",
            "group_id": None,
            "org_id": None,
            "parent_id": 0
        }
        response_create_suite = api_create_suite.post(data=data_create_suite, verify=False)
        api_create_suite.session.close()  # 在创建时打开session, 在这关闭就行了.
        response_create_suite_dict = TestManualJob._parse_response_json_to_dict(response_create_suite.text)
        self.assertEqual(response_create_suite_dict.get("error_code"), f"{RET.OK}", "创建suite失败")

        # 创建case
        logger.info("创建case")
        api_create_case = RestApi(server_url + "/api/v1/case", auth=self.auth)
        data_create_case = {
            "name": TestManualJob.CASE_NAME,
            "suite": TestManualJob.SUITE_NAME,
            "description": TestManualJob.CASE_DESCRIPTION,
            "preset": TestManualJob.CASE_PRESET,
            "expection": TestManualJob.CASE_EXPECTION,
            "steps": "".join(TestManualJob.STEP_OPERATION[1::]),
            "automatic": False,
            "usabled": True,
            "code": None,
            "group_id": None,
            "org_id": None,
            "machine_num": 1,
            "machine_type": "kvm",
            "add_network_interface": None,
            "add_disk": None,
            "remark": None,
            "deleted": False,
            "owner": None,
            "git_repo_id": None,
            "permission_type": "person"
        }
        response_create_case = api_create_case.post(data=data_create_case, verify=False)
        api_create_case.session.close()
        response_create_case_dict = TestManualJob._parse_response_json_to_dict(response_create_case.text)
        self.assertEqual(response_create_case_dict.get("error_code"), f"{RET.OK}", "创建case失败")
        TestManualJob.CASE_ID = response_create_case_dict.get("data").get("case_id")  # 添加类变量case_id
        logger.info("创建的case的id是" + str(TestManualJob.CASE_ID))

        # 创建milestone
        logger.info("创建milestone")
        api_create_milestone = RestApi(server_url + "/api/v2/milestone", auth=self.auth)
        data_create_milestone = {
            "name": TestManualJob.MILESTONE_NAME,
            "description": "test_milestone_description_" + self.CURTIME,
            "state": "active",
            "product_id": 1,  # 实际并没有这个product, 这个字段不能填null, 就随便写了一个
            "type": "release",
            "start_time": TestManualJob.DATETIME_CURTIME.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (TestManualJob.DATETIME_CURTIME + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "is_sync": False,
            "creator_id": gitee_id,
            "permission_type": "person",
            "org_id": 1  # 实际并没有这个org, 这个字段不能填null, 就随便写了一个
        }
        response_create_milestone = api_create_milestone.post(data=data_create_milestone, verify=False)
        api_create_milestone.session.close()
        response_create_milestone_dict = TestManualJob._parse_response_json_to_dict(response_create_milestone.text)
        self.assertEqual(response_create_milestone_dict.get("error_code"), f"{RET.OK}", "创建milestone失败")

        # 获取刚添加这个新建的milestone的id
        logger.info("查询以获取刚创建的这个milestone的id")
        api_query_milestone = RestApi(server_url + "/api/v2/milestone?page_size=999999", auth=self.auth)
        response_query_milestone = api_query_milestone.get2(verify=False)
        api_query_milestone.session.close()
        response_query_milestone_dict = TestManualJob._parse_response_json_to_dict(response_query_milestone.text)
        self.assertEqual(response_query_milestone_dict.get("error_code"), f"{RET.OK}", "创建milestone失败")
        milestone_list = response_query_milestone_dict.get("data").get("items")
        for each in milestone_list:
            if each.get("name") == TestManualJob.MILESTONE_NAME:
                TestManualJob.MILESTONE_ID = each.get("id")
                break
        logger.info("创建的milestone的id是" + str(TestManualJob.MILESTONE_ID))

    def test02_create_manual_job(self):
        """
            基于test01中创建的case, 创建2个manual_job
        """
        logger.info("test02_创建2个manual_job")
        api = RestApi(server_url + TestManualJob._get_manual_job_event_url(), auth=self.auth)
        for cnt in range(2):
            data = {
                "case_id": TestManualJob.CASE_ID,
                "name": TestManualJob.MANUAL_JOB_NAME[cnt],
                "milestone_id": TestManualJob.MILESTONE_ID
            }
            response = api.post(data=data, verify=False)
            api.session.close()
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "创建manual_job失败")
            TestManualJob.MANUAL_JOB_ID[cnt] = response_dict.get("data").get("id")

        logger.info("创建的manual_job的id是" + str(TestManualJob.MANUAL_JOB_ID))

    def test03_query_manual_job(self):
        """
            查询status=0(进行中, 刚创建的manual_job处于这种状态)的manual_job, 以查到test02中创建的manual_job
        """
        logger.info("test03_查询状态为\"进行中\"的manual_job")
        api = RestApi(server_url + TestManualJob._get_manual_job_event_url(status=0), auth=self.auth)
        response = api.get2(verify=False, params={"page_size": 999999})
        api.session.close()
        response_dict = TestManualJob._parse_response_json_to_dict(response.text)
        self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "查询manual_job列表失败")
        manual_job_list = response_dict.get("data").get("items")
        for cnt in range(2):
            for each in manual_job_list:
                if each.get("id") == TestManualJob.MANUAL_JOB_ID[cnt]:
                    if each.get("case_id") != TestManualJob.CASE_ID or each.get(
                            "milestone_name") != TestManualJob.MILESTONE_NAME:
                        logger.error("没有查到test02中创建的manual_job")
                    else:
                        logger.info("查到test02中创建的manual_job信息: " + str(each))
                    break
            else:
                logger.error("没有查到test02中创建的manual_job")

    def test04_enter_manual_job_logs(self):
        """
            给test02中创建的manual_job录入日志
        """
        logger.info("test04_给test02中创建的manual_job录入日志: 执行结果全部与预期一致")
        for cnt in range(2):
            for step in range(1, TestManualJob.TOTAL_STEP + 1):
                api = RestApi(
                    server_url + TestManualJob._get_manual_job_log_event_url(TestManualJob.MANUAL_JOB_ID[cnt]),
                    auth=self.auth)
                data = {
                    "step": step,
                    "content": TestManualJob.LOG_CONTENT[step],
                    "passed": True  # 全部通过
                }
                response = api.put(data=data, verify=False)
                api.session.close()
                response_dict = TestManualJob._parse_response_json_to_dict(response.text)
                self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "manual_job录入日志失败")

    def test05_modify_manual_job_log(self):
        """
            修改后一个manual_job的日志, 使其某个步骤的执行结果与预期不一致
        """
        logger.info("修改后一个manual_job的日志, 使其某个步骤的执行结果与预期不一致")
        api = RestApi(server_url + TestManualJob._get_manual_job_log_event_url(TestManualJob.MANUAL_JOB_ID[1]))
        TestManualJob.MODIFY_STEP = random.randint(1, TestManualJob.TOTAL_STEP)
        data = {
            "step": TestManualJob.MODIFY_STEP,
            "content": TestManualJob.MODIFY_LOG_CONTENT,
            "passed": False
        }
        response = api.put(data=data, verify=False)
        api.session.close()
        TestManualJob._parse_response_json_to_dict(response.text)

    def test06_query_manual_job_log(self):
        """
            查询test04和test05中录入的manual_job的日志
        """
        logger.info("test06_查询test04和test05中录入和修改的manual_job的日志")
        for cnt in range(2):
            for step in range(1, TestManualJob.TOTAL_STEP + 1):
                api = RestApi(
                    server_url + TestManualJob._get_manual_job_log_query_event_url(
                        TestManualJob.MANUAL_JOB_ID[cnt],
                        step
                    ), auth=self.auth)
                response = api.get2(verify=False)
                api.session.close()
                response_dict = TestManualJob._parse_response_json_to_dict(response.text)
                self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "查询manual_job日志失败")
                logger.info(response_dict.get("data"))
                self.assertEqual(response_dict.get("data").get("operation"),
                                 TestManualJob.STEP_OPERATION[step].rstrip("\n"), "查询manual_job日志不正确")

    def test07_submit_manual_job(self):
        """
            提交完成test02中创建的2个manual_job, 查询状态为1(已完成)的manual_job查到它们的状态
        """
        logger.info("test07_提交完成test02中创建的2个manual_job, 查询状态为1(已完成)的manual_job以检查它们的状态")
        for cnt in range(2):
            api_submit = RestApi(
                server_url + TestManualJob._get_manual_job_submit_event_url(TestManualJob.MANUAL_JOB_ID[cnt]),
                auth=self.auth)
            response = api_submit.post(verify=False)
            api_submit.session.close()
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "提交manual_job失败")

        # 查询
        logger.info("查询状态为\"已完成\"的manual_job")
        for cnt in range(2):
            api_query = RestApi(TestManualJob._get_manual_job_event_url(status=1), auth=self.auth)
            response = api_query.get(verify=False, params={"page_size": 999999})
            api_query.session.close()
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "查询manual_job列表失败")
            response_dict_manual_job_list = response_dict.get("data").get("items")
            for each in response_dict_manual_job_list:
                if each.get("id") == TestManualJob.MANUAL_JOB_ID[cnt]:
                    if each.get("case_id") != TestManualJob.CASE_ID or \
                            each.get("milestone_name") != TestManualJob.MILESTONE_NAME:
                        logger.error("没有查到添加的manual_job")
                    elif (cnt == 0 and each.get("result") == 0) or (cnt == 1 and each.get("result") == 1):
                        logger.error("manual_job的结果不对")
                    else:
                        logger.info(each)
                    break
            else:
                logger.error("没有查到添加的manual_job")

    def test08_delete_manual_job_log(self):
        """
            删除test04中录入的, 由test02中创建的前一个manual_job的随机一个步骤的日志
        """
        logger.info("test08_删除test04中录入的, 由test02中创建的前一个手工测试任务的随机一个步骤的日志")
        api = RestApi(server_url + TestManualJob._get_manual_job_log_event_url(TestManualJob.MANUAL_JOB_ID[0]),
                      auth=self.auth)
        TestManualJob.DELETE_STEP = random.randint(1, TestManualJob.TOTAL_STEP)
        data = {
            "step": TestManualJob.DELETE_STEP
        }
        response = api.delete(data=data, verify=False)
        api.session.close()
        response_dict = TestManualJob._parse_response_json_to_dict(response.text)
        self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "提交manual_job失败")

        # 查询
        for step in range(1, TestManualJob.TOTAL_STEP + 1):
            api = RestApi(
                server_url + TestManualJob._get_manual_job_log_query_event_url(TestManualJob.MANUAL_JOB_ID[0], step),
                auth=self.auth
            )
            response = api.get2(verify=False)
            api.session.close()
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "查询manual_job日志失败")
            logger.info(response_dict.get("data"))
            if step == TestManualJob.DELETE_STEP:
                self.assertEqual(response_dict.get("data").get("content"), None, "删除manual_job日志不成功")
                self.assertEqual(response_dict.get("data").get("passed"), None, "删除manual_job日志不成功")

    def test09_delete_manual_job(self):
        """
            删除test02中创建的2个manual_job
        """
        logger.info("test09_删除test02中创建的2个manual_job")
        for cnt in range(2):
            api_delete = RestApi(
                server_url + TestManualJob._get_manual_job_delete_event_url(TestManualJob.MANUAL_JOB_ID[cnt]),
                auth=self.auth)
            response = api_delete.delete(verify=False)
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "删除manual_job失败")

        # 再查询, 应查不到
        logger.info("查询状态为\"进行中\"和\"已完成\"的manual_job")
        for status in range(2):
            api = RestApi(server_url + TestManualJob._get_manual_job_event_url(status=status), auth=self.auth)
            response = api.get2(verify=False, params={"page_size": 999999})
            api.session.close()
            response_dict = TestManualJob._parse_response_json_to_dict(response.text)
            self.assertEqual(response_dict.get("error_code"), f"{RET.OK}", "查询manual_job列表失败")
            manual_job_list = response_dict.get("data").get("items")
            for cnt in range(2):
                for each in manual_job_list:
                    if each.get("id") == TestManualJob.MANUAL_JOB_ID[cnt]:
                        logger.error("查到了test02中创建的manual_job, 删除失败")
                        break
                else:
                    logger.info("没有查到test02中创建的manual_job")


if __name__ == "__main__":
    unittest.main()
