# -*- coding: utf-8 -*-
# @Author : GaoDi
# @Date   : 2021-08-30 19:51:54
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :

from server.utils.requests_util import do_request

GITEE_HTTP_PREFIX = "https://gitee.com/api/v5"


class GiteeApi(object):
    class Oauth:

        @staticmethod
        def callback(code, client_id, redirect_uri, client_secret):
            """
            gitee oauth verify
            :param code: Type[str] git user code
            :param client_id: Type[str] oauth client id
            :param redirect_uri: Type[str] oauth redirect uri
            :param client_secret: Type[str] oauth client secret
            :return: Type[dict]
            """
            url = f"https://gitee.com/oauth/token"
            params = {
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            body = dict(client_secret=client_secret)
            resp = {}
            r = do_request("post", url, params=params, body=body, obj=resp)
            if r != 0 or not resp.get("access_token"):
                return False, {}
            return True, resp

    class User:
        HTTP_PREFIX = f"{GITEE_HTTP_PREFIX}/user"

        @staticmethod
        def get_info(access_token):
            url = GiteeApi.User.HTTP_PREFIX
            params = {"access_token": access_token}
            resp = {}
            r = do_request("get", url, params=params, obj=resp)
            if r != 0 or not resp.get("id"):
                return False, {}
            return True, resp
