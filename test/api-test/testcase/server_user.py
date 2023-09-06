import json
import unittest
from datetime import datetime
import os
import sys
import pytz
sys.path.append(os.path.split(os.path.abspath(os.path.dirname(__file__)))[0])

import redis

from lib import logger
from lib.constant import RET, server_url
from lib.constant import tmp_user_token, tmp_gitee_id, user_token, gitee_id, new_gitee_id
from lib.constant import gitee_oauth_id, gitee_oauth_redirect_url, gitee_oauth_scope
from lib.constant import redis_url
from lib.common import AdminAuthUnittestTestCase, RestApi


class TestUser(AdminAuthUnittestTestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("------------test user interface start------------")
        super().setUpClass()
        cls.curtime = datetime.now(pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S")
    
    def setUp(self):
        self.gitee_oauth_login_url = "https://gitee.com/oauth/authorize?" \
            "client_id={}" \
            "&redirect_uri={}"  \
            "&response_type=code&scope={}".format(
                gitee_oauth_id,
                gitee_oauth_redirect_url,
                gitee_oauth_scope
            )
        self.tmp_token = f"JWT {tmp_user_token}"
        self.token = f"JWT {user_token}"

        api_org = RestApi(
            f"{server_url}/api/v1/admin/org"
        )
        
        org_name = "testorg" + self.curtime
        data = {
            "name": org_name,
            "description": "test organization"
        }
        resp = api_org.post(data=data)
        self.org_id = json.loads(resp.text).get("data").get("id")

        api_org.session.close()
    
    def test_gitee_login(self): 
        logger.info("验证码云Oauth2鉴权登录")
        api_gitee_login = RestApi(
            f"{server_url}/api/v1/gitee/oauth/login?org_id={self.org_id}",
            auth=self.tmp_token
        )
        resp = api_gitee_login.get()
        self.assertIn(
            self.gitee_oauth_login_url,
            resp.text,
            "验证码云Oauth2鉴权登录失败!"
        )

        api_gitee_login.session.close()

    def test_login(self):
        rapi = RestApi(self.gitee_oauth_login_url)
        request_url = rapi.get()
        rapi.session.close()

        logger.info("验证基于码云Oauth鉴权赋予的code的本地登录")
        api_login = RestApi(request_url)
        resp = api_login.get()
        self.assertIn(
            "?isSuccess=True",
            resp.text,
            "验证基于码云Oauth鉴权赋予的code的本地登录失败!"
        )
        
        api_login.session.close()

    def test_logout(self):
        logger.warning("运行logout用例将会使配置文件中的tmp_user_token失效")
        pool = redis.ConnectionPool.from_url(redis_url)
        redis_client = redis.StrictRedis(connection_pool=pool)
        
        logger.info("验证用户本地登出")
        api_logout = RestApi(
            f"{server_url}/api/v1/logout",
            auth=self.tmp_token
        )
        _ = api_logout.delete()
        token = redis_client.get(f"token_{tmp_gitee_id}")
        self.assertIsNone(
            token,
            "验证用户本地登出失败!"
        )

        api_logout.session.close()

    def test_users(self):
        logger.info("验证get获取平台用户列表")
        api_users = RestApi(
            f"{server_url}/api/v1/users",
            auth=self.token
        )
        resp = api_users.get()
        self.assertIn(
            f'"gitee_id":"{gitee_id}"',
            resp.text,
            "验证get获取平台用户列表失败"
        )

    def test_user_item(self):
        api_user_item = RestApi(
            f"{server_url}/api/v1/users/{new_gitee_id}"
        )

        logger.info("验证post注册指定用户信息")
        data = {
            "organization_id": self.org_id,
        }
        resp = api_user_item.post(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post注册指定用户信息失败!"
        )

        logger.info("验证get获取指定用户信息")
        resp = api_user_item.get()
        self.assertIn(
            f'"gitee_id":"{new_gitee_id}"',
            resp.text,
            "验证get获取指定用户信息失败!"
        )

        api_user_item.session.close()

        api_user_item = RestApi(
            f"{server_url}/api/v1/users/{gitee_id}",
            auth=self.token
        )

        logger.info("验证put编辑指定用户信息")
        data = {
            "phone": "13813881388"
        }
        resp = api_user_item.put(data=data)
        self.assertIn(
            f'"error_code":"{RET.OK}"',
            resp.text,
            "验证post注册指定用户信息失败!"
        )

        api_user_item.session.close()

    def test_org(self):
        pass

    def test_group(self):
        pass

    def test_user_task(self):
        pass

    def test_user_machine(self):
        pass

    def test_user_case_commit(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("------------test user interface end--------------")
    
if __name__ == "__main__":
    unittest.main()