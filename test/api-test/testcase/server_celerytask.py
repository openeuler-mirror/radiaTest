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
from lib.constant import gitee_id, RET, repo_url, server_url
from lib.common import UserAuthUnittestTestCase, RestApi, get_val_by_key_val, get_val_by_key_val2


class TestCelerytask(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test celerytask start------------")
        super().setUpClass()

    def setUp(self):
        self.api_celerytask = RestApi(
            f"{server_url}/api/v1/celerytask", 
            auth=self.auth
        )

    def test_celerytask(self):
        logger.info("验证post创建celery后台任务数据")
        data = {
            "tid": "thisisatestcelerytask",
            "status": "STARTING",
            "object_type": "script"
        }
        respon = self.api_celerytask.post(data=data)
        self.assertIn(
            f'"error_code": "{RET.OK}"', 
            respon.text,
            "验证post创建celery后台任务数据失败!"
        )

        logger.info("验证get获取celery后台任务数据")
        respon = self.api_celerytask.get()
        self.assertIn(
            "thisisatestcelerytask",
            respon.text,
            "验证get获取celery后台任务数据失败!"
        )

    def tearDown(self) -> None:
        self.api_celerytask.session.close()
       
    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test mirroring end--------------")
    
if __name__ == "__main__":
    unittest.main()