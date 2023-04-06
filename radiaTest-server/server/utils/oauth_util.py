from flask import current_app

from server.utils.requests_util import do_request


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
            r = do_request(
                "post",
                url,
                params=params,
                body=body,
                obj=resp,
                encoder=None
            )
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
            r = do_request(
                "get",
                url,
                params=params,
                obj=resp,
                headers=headers
            )

            if r != 0:
                return False, {}

            if authority == "oneid":
                current_app.logger.info("oneid info:{}".format(resp.get("data")))
                return True, resp.get("data")
            current_app.logger.info("gitee info:{}".format(resp))
            return True, resp
