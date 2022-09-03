# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : disnight
# @email   : fjc837005411@outlook.com
# @Date    : 2022/07/30
# @License : Mulan PSL v2
#####################################

import os
import unittest

from lib import logger


class TestMdUtil(unittest.TestCase):
    TEST_MD_FILEPATH = os.path.join(os.path.dirname(__file__), "test.md")
    
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("------------test markdown util start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")

    def _get_md_content(self) -> str:
        result = ""
        with open(self.TEST_MD_FILEPATH, "r", encoding="utf-8") as f:
            result = f.read()
        return result

    def test_parse_simple_md_table(self):
        pass

    def test_parse_multi_md_table(self):
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test markdown util end--------------")
