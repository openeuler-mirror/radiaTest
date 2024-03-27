# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from server.utils.requests_util import do_request, HttpRequestParam


class LoginApi(object):
    class Oauth:

        @staticmethod
        def callback(url, code, client_id, redirect_uri, client_secret):
            """
            oauth verify
            :param url: Type[str] oauth get token url
            :param code: Type[str] oauth user code
            :param client_id: Type[str] oauth client id
            :param redirect_uri: Type[str] oauth redirect uri
            :param client_secret: Type[str] oauth client secret
            :return: Type[dict]
            """
            params = {
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            body = dict(client_secret=client_secret)
            resp = {}
            http_request_param = HttpRequestParam(
                "post",
                url,
                params=params,
                body=body,
                obj=resp,
                encoder=None
            )
            r = do_request(http_request_param)
            if r != 0 or not resp.get("access_token"):
                return False, {}
            return True, resp

    class User:

        @staticmethod
        def get_info(url, access_token, authority):
            if authority == "oneid":
                params = {}
                headers = {
                    "Authorization": access_token,
                    "Content-Type": "application/json",
                }
            else:
                params = {
                    "access_token": access_token
                }
                headers = {"Content-Type": "application/json"}
            resp = {}
            http_request_param = HttpRequestParam(
                "get",
                url,
                params=params,
                obj=resp,
                headers=headers
            )
            r = do_request(http_request_param)

            if r != 0:
                return False, {}

            if authority == "oneid":
                return True, resp.get("data")

            return True, resp
