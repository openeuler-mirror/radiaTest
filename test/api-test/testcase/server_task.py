import json
import unittest
from datetime import datetime
import os
import sys
import pytz
sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])

from lib import logger
from lib.constant import RET, server_url
from lib.common import UserAuthUnittestTestCase, RestApi


class TestTask(UserAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test task interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test task interface end--------------")
    
if __name__ == "__main__":
    unittest.main()