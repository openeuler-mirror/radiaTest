import abc
from datetime import datetime
import json

from flask.globals import current_app
import requests
from flask import g, jsonify

from server import redis_client
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert, Edit, Delete
from server.utils.response_util import RET
from server.model.organization import Organization
from server.model.milestone import Milestone
from server.schema.milestone import GiteeMilestoneBase, GiteeMilestoneEdit


class BaseOpenApiHandler:    
    def __init__(self, table=None, namespace=None):
        self.table = table
        self.namespace = namespace

    @abc.abstractmethod
    def gitee_2_radia(self):
        pass

    @abc.abstractmethod
    def radia_2_gitee(self):
        pass

    @property
    def access_token(self):
        return redis_client.hget(
            RedisKey.user(g.gitee_id),
            'gitee_access_token'
        )

    @property
    def current_org(self):
        org_id = redis_client.hget(
            RedisKey.user(g.gitee_id),
            'current_org_id'
        )
        org = Organization.query.filter_by(id=org_id).first()
        return org

    @collect_sql_error
    def add_update(self, act, url, data, handler):
        data.update({
            "access_token": self.access_token
        })

        _resp = requests.request(
            method=act,
            url=url,
            data=GiteeMilestoneBase(**data).__dict__,
            headers=current_app.config.get("HEADERS")
        )

        _resp.encoding = _resp.apparent_encoding
        
        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            return jsonify(error_code=RET.BAD_REQ_ERR, error_msg="fail to add_update through gitee v8 openAPI")
        
        gitee_milestone = json.loads(_resp.text)

        milestone = self.gitee_2_radia(gitee_milestone)

        _ = handler(self.table, milestone).single(self.table, self.namespace)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @collect_sql_error
    def query(self, url, params):
        _resp = requests.get(
            url=url,
            params={
                "access_token": self.access_token,
                **params,
            },
            headers=current_app.config.get("HEADERS")
        )

        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            return jsonify(error_code=RET.BAD_REQ_ERR, error_msg="fail to get data through gitee openAPI")
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_resp.text
        )


class MilestoneOpenApiHandler(BaseOpenApiHandler): 
    def __init__(self, body=None):
        if body is not None:
            self.body = self.radia_2_gitee(body)
        super().__init__(Milestone, "/milestone")

    def gitee_2_radia(self, body):
        if isinstance(body.get("start_date"), str):
            body["start_time"] = datetime.strptime(
                body.get("start_date"), 
                "%Y-%m-%d"
            )

        if isinstance(body.get("due_date"), str):
            body["end_time"] = datetime.strptime(
                body.get("due_date"), 
                "%Y-%m-%d"
            )

        return body
    
    def radia_2_gitee(self, body):
        if isinstance(body.get("start_time"), datetime):
            body["start_time"] = body.get("start_time").strftime("%Y-%m-%d")

        if isinstance(body.get("end_time"), datetime):
            body["end_time"] = body.get("end_time").strftime("%Y-%m-%d")
        
        return body

    @collect_sql_error
    def create(self):
        _url = "https://api.gitee.com/enterprises/{}/milestones".format(
            self.current_org.enterprise_id
        )

        return self.add_update(
            act="POST",
            url=_url,
            data=self.body,
            handler=Insert,
        )

    def udpate(self, milestone_id):
        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone_id,
        )
        return self.add_update(
            act="PUT",
            url=_url,
            data=self.body,
            handler=Edit,
        )
    
    def delete(self, milestone_id):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="the milestone not exist")

        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone_id,
        )
        _resp = json.loads(self.query(_url, {}).text)
        if _resp.get("error_code") == RET.OK:
            if _resp.get("data").get("title") == milestone.name:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR, 
                    error_msg="you should delete this milestone in e.gitee.com first"
                )
        
        return Delete(
            Milestone, 
            {"id": milestone_id}
        ).single(Milestone, "/milestone")


class IssueOpenApiHandlerV5:
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


class IssueOpenApiHandlerV8(BaseOpenApiHandler):
    def get_all_v8(self, params):
        _url = "https://api.gitee.com/enterprises/{}/issues".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url,params=params)
