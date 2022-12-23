# -*- coding:utf-8 -*-

import json
from copy import deepcopy
import unittest
import requests


from lib import constant, logger


class AdminAuthUnittestTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("初始化: 获取最高权限授权token")
        resp = requests.post(
            url=f"{constant.server_url}/api/v1/admin/login",
            data=json.dumps(
                {
                    "account": constant.account,
                    "password": constant.password,
                }
            ),
            headers=constant.default_headers
        )
        try:
            token = json.loads(resp.text)["data"]["token"]
            cls.auth = f"JWT {token}"
        except json.decoder.JSONDecodeError as e:
            logger.error(str(e))
    
    @classmethod
    def tearDownClass(cls) -> None:
        logger.info("环境清理: 登出授权token")
        resp = requests.delete(
            url=f"{constant.server_url}/api/v1/logout",
            headers={
                "Authorization": cls.auth,
                **constant.default_headers
            }
        )
        if resp.status_code != 200:
            logger.error(f"Error: {resp.text}")
        try:
            code = json.loads(resp.text).get("error_code")
            msg = json.loads(resp.text).get("error_msg")
            if code != constant.RET.OK:
                raise logger.error(f"Error: {msg}")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Error: {str(e)}")
        

class UserAuthUnittestTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logger.info("初始化: 使用配置文件中配置的用户token")
        cls.auth = f"JWT {constant.user_token}"


class RestApi:
    def __init__(self, api_url, **kwargs):
        self.api_url = api_url
        self.session = requests.session()
        self.header = constant.default_headers
        if kwargs.get("auth"):
            self.set_auth(kwargs.get("auth"))
            
    def set_auth(self, jwt: str):
        """
        set authorized JWT signature to headers of this API

        :param jwt: the JWT signature of headers of authorized requests
        """
        self.header.update(
            {
                "Authorization": jwt
            }
        )

    def get(self, **kwargs):
        return self.session.get(
            f"{constant.server_url}{self.api_url}", 
            headers=self.header, 
            **kwargs
        )

    def get2(self, **kwargs):
        return self.session.get(
            self.api_url, 
            headers=self.header, 
            **kwargs
        )


    def post(self, data=None, **kwargs):
        return self.session.post(
            self.api_url, 
            data=json.dumps(data), 
            headers=self.header, **kwargs
        )

    def post2(self, data=None, **kwargs):
        _header = deepcopy(self.header)
        # 提交采用form表单格式的数据时，去除默认的内容格式application/json
        _header.pop("Content-Type")
        #当提交的是form表单形式的数据时，data数据不需要使用json.dumps()将字典类型转换为字符串类型
        return self.session.post(
            self.api_url,
            data=data, 
            headers=_header, 
            **kwargs
        )

    def put(self, data=None, **kwargs):
        return self.session.put(
            self.api_url,
            data=json.dumps(data), 
            headers=self.header, 
            **kwargs
        )

    def put2(self, data=None, **kwargs):
        _header = deepcopy(self.header)
        # 提交采用form表单格式的数据时，去除默认的内容格式application/json
        _header.pop("Content-Type")
        #当提交的是form表单形式的数据时，data数据不需要使用json.dumps()将字典类型转换为字符串类型
        return self.session.put(
            self.api_url,
            data=data, 
            headers=self.header,
            **kwargs
        )

    def delete(self, data=None, **kwargs):
        return self.session.delete(
            self.api_url, 
            data=json.dumps(data),
            headers=self.header,
            **kwargs
        )


def str_to_arrdict(string: str):
    string = string.strip()
    string = string[1:]
    string = string[:-1]
    arrdict = string.split("},{")
    arrdict_len = len(arrdict)
    if arrdict_len == 1:
        arrdict[0] = json.loads(arrdict[0])
        return arrdict
    elif arrdict_len == 2:
        arrdict[0] = json.loads(arrdict[0] + "}")
        arrdict[1] = json.loads("{" + arrdict[1])
    else:
        arrdict[0] = json.loads(arrdict[0] + "}")
        arrdict[arrdict_len - 1] = json.loads("{" + arrdict[arrdict_len - 1])
        for i in range(1, arrdict_len - 1):
            arrdict[i] = json.loads("{" + arrdict[i] + "}")
    return arrdict


def index_arrdict(k: str, num: str, arr: list):
    for i, item in arr:
        if num == item[k]:
            return i
    return -1


def get_val_by_key_val(k1: str, v1: str, k2: str, res: str):
    rs = json.loads(res)
    data = rs["data"]
    for dt in data:
        if dt[k1] == v1:
            return dt[k2]
    return ""


def get_val_by_key_val2(k1: str, v1: str, k2: str, res: str):
    rs = json.loads(res)
    data = rs["data"]
    items = data["items"]
    for dt in items:
        if dt[k1] == v1:
            return dt[k2]
    return ""