import json

from flask.globals import current_app
import requests
from flask import g, jsonify

from server import redis_client
from server.utils.redis_util import RedisKey


class HandlerIssuesList:

    def __init__(self, enterprise, milestone) -> None:
        self.url = "https://gitee.com/api/v5/enterprises/{}/issues".format(
            enterprise,
        )

        self.access_token = redis_client.hget(
            RedisKey.user(g.gitee_id),
            'gitee_access_token'
        )

        self.total_count, self.total_page = self._get_summary(
            enterprise,
            milestone,
        )

    def _get_summary(self, enterprise, milestone):
        _resp = requests.get(
            url=self.url,
            params={
                "access_token": self.access_token,
                "enterprise": enterprise,
                "milestone": milestone,
                "state": "all",
                "page": 1,
                "per_page": current_app.config.get("ISSUES_PER_PAGE") if current_app.config.get(
                    "ISSUES_PER_PAGE") else 100,
            },
            headers=current_app.config.get("HEADERS") if current_app.config.get("HEADERS") else None
        )
        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code == 200:
            return (
                int(_resp.headers.get("total_count")),
                int(_resp.headers.get("total_page"))
            )
        else:
            return (0, 0)

    def get_all_list(self, params):
        _total_data = []

        for page in range(self.total_page):
            _resp = requests.get(
                url=self.url,
                params={
                    "access_token": self.access_token,
                    "enterprise": params["enterprise"],
                    "state": params["state"],
                    "sort": params["sort"],
                    "direction": params["direction"],
                    "page": page + 1,
                    "per_page": current_app.config.get("ISSUES_PER_PAGE") if current_app.config.get(
                        "ISSUES_PER_PAGE") else 100,
                    "milestone": params["milestone"]
                },
                headers=current_app.config.get("HEADERS") if current_app.config.get("HEADERS") else None
            )

            if _resp.status_code == 200:
                _total_data += json.loads(_resp.text)

        return _total_data

    def getAll(self, params):
        total_data = self.get_all_list(params=params)
        return jsonify(total_data)