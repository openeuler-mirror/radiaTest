import abc
from datetime import datetime
import json, os

from flask.globals import current_app
import requests
from flask import g, jsonify

from server import redis_client
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert, Edit, Delete
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.model.organization import Organization
from server.model.milestone import Milestone
from server.model.template import Template
from server.schema.milestone import GiteeMilestoneBase, GiteeMilestoneEdit
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from server.utils.permission_utils import PermissionManager, GetAllByPermission
from server.utils.resource_utils import ResourceManager

class CreateMilestone:
    @staticmethod
    def bind_scope(milestone_id, body, api_info_file):
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split("/")[-1], "")
        allow_list, deny_list = PermissionManager().get_api_list("milestone", cur_dir + api_info_file, milestone_id)
        PermissionManager().generate(allow_list, deny_list, body)
    
    @staticmethod
    def run(body):
        if body.get("is_sync"):
            MilestoneOpenApiHandler(body).create()
            milestone =  Milestone.query.filter_by({"name":body.get("name")}).first()
            CreateMilestone.bind_scope(milestone.id, body, "api_infos.yaml")
            return jsonify(
                error_code=RET.OK, error_msg="Request processed successfully."
            )
        else:
            try:
                milestone_id = Insert(Milestone, body).insert_id(Milestone, '/milestone')
            except (IntegrityError, SQLAlchemyError) as e:
                raise RuntimeError(str(e))
            CreateMilestone.bind_scope(milestone_id, body, "api_infos.yaml")
            return jsonify(
                error_code=RET.OK, error_msg="Request processed successfully."
            )

class DeleteMilestone:
    @staticmethod
    def single(milestone_id):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} does not exist".format(milestone_id)
            )

        if milestone.is_sync is True:
            MilestoneOpenApiHandler().delete(milestone_id)
        else:
            ResourceManager("milestone").del_cascade_single(milestone_id, Template, [Template.milestone_id==milestone_id], False)
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )

class MilestoneHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = GetAllByPermission(Milestone).get_filter()
        
        if query.name:
            filter_params.append(Milestone.name.like(f"%{query.name}%"))
        if query.type:
            filter_params.append(Milestone.type == query.type)
        if query.state:
            filter_params.append(Milestone.state == query.state)
        if query.is_sync:
            filter_params.append(Milestone.is_sync == query.is_sync)
        
        query_filter = Milestone.query.filter(*filter_params).order_by(Milestone.create_time)

        def page_func(item):
            milestone_dict = item.to_json()
            return milestone_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, 
            query.page_size, 
            func=page_func
        )
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get milestone page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)




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
    def add_update(self, act, url, data, schema, handler):
        data.update({
            "access_token": self.access_token
        })

        _resp = requests.request(
            method=act,
            url=url,
            data=json.dumps(schema(**data).__dict__),
            headers=current_app.config.get("HEADERS")
        )

        _resp.encoding = _resp.apparent_encoding

        if (_resp.status_code != 200 and act == "PUT") \
            or (_resp.status_code != 201 and act == "POST"):
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
    def query(self, url, params=None):
        _params = {
            "access_token": self.access_token,
        }
        if params is not None and isinstance(params, dict):
            _params.update(params)
            
        _resp = requests.get(
            url=url,
            params=_params,
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
            self.type = body.get("type")
            self.product_id = body.get("product_id")
            self.body = self.radia_2_gitee(body)
        super().__init__(Milestone, "/milestone")

    def gitee_2_radia(self, body):
        if isinstance(body.get("start_date"), str):
            body["start_time"] = body.get("start_date")

        if isinstance(body.get("due_date"), str):
            body["end_time"] = body.get("due_date")

        body.update({
            "name": body.get("title"),
            "type": self.type,
            "product_id": self.product_id,
            "is_sync": True,
        })

        return body
    
    def radia_2_gitee(self, body):
        if isinstance(body.get("start_time"), str):
            body["start_time"] = body.get("start_time")

        if isinstance(body.get("end_time"), str):
            body["end_time"] = body.get("end_time")
        
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
            schema=GiteeMilestoneBase,
            handler=Insert,
        )

    def edit(self, milestone_id):
        _url = "https://api.gitee.com/enterprises/{}/milestones/{}".format(
            self.current_org.enterprise_id,
            milestone_id,
        )
        return self.add_update(
            act="PUT",
            url=_url,
            data=self.body,
            schema=GiteeMilestoneEdit,
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
        
        return ResourceManager("milestone").del_cascade_single(milestone_id, Template, [Template.milestone_id==milestone_id], False)


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
    def get_all(self, params):
        _url = "https://api.gitee.com/enterprises/{}/issues".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url,params=params)
    
    def get_issue_types(self):
        _url = "https://api.gitee.com/enterprises/{}/issue_types".format(
            self.current_org.enterprise_id,
        )
        return self.query(url=_url)