import json
import requests

from flask import current_app

from server.utils.response_util import RET


class PermissionItemsPool:
    def __init__(self, origin_pool, namespace, act, auth):
        self.origin_pool = origin_pool
        self._root_url = "api/{}/{}".format(
            current_app.config.get("OFFICIAL_API_VERSION"), 
            namespace
        )
        self.act = act
        self.auth = auth

    def _get_items(self, eft):
        return_data = []
        for _item in self.origin_pool:
            try:
                _url = "{}/{}".format(self._root_url, _item.id)
                _resp = requests.request(
                    method=self.act,
                    url="{}://{}:{}/{}".format(
                        current_app.config.get("PROTOCOL"),
                        current_app.config.get("SERVER_IP"),
                        current_app.config.get("SERVER_PORT"),
                        _url
                    ),
                    headers={
                        'Content-Type': 'application/json;charset=utf8',
                        'Authorization': self.auth,
                    },
                )
                if _resp.status_code != 200:
                    raise RuntimeError(_resp.text)

                _output = json.loads(_resp.text)

                if (_output.get("error_code") != RET.UNAUTHORIZE_ERR) == (eft == "allow"):
                    return_data.append(_item.id)

            except Exception as e:
                current_app.logger.warn(str(e))
                continue
        
        return return_data

    @property
    def allow_list(self):
        return self._get_items("allow")

    @property
    def deny_list(self):
        return self._get_items("deny")