from server.utils.requests_util import do_request

GITEE_HTTP_PREFIX_V5 = "https://gitee.com/api/v5"
GITEE_HTTP_PREFIX_V8 = "https://api.gitee.com/enterprises"


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
        HTTP_PREFIX_V5 = f"{GITEE_HTTP_PREFIX_V5}/user"
        HTTP_PREFIX_V8 = f"{GITEE_HTTP_PREFIX_V8}/users"

        @staticmethod
        def get_info(access_token):
            url_v5 = GiteeApi.User.HTTP_PREFIX_V5
            url_v8 = GiteeApi.User.HTTP_PREFIX_V8

            params = {"access_token": access_token}
            resp = {}
            r = do_request("get", url_v8, params=params, obj=resp)
            if r != 0 or not resp.get("id"):
                r = do_request("get", url_v5, params=params, obj=resp)
                if r != 0 or not resp.get("id"):
                    return False, {}

                return True, resp

            return True, resp
