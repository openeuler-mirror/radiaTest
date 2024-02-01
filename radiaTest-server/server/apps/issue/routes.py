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

import json
from flask import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server import swagger_adapt
from server.schema.base import QueryBaseModel
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model.milestone import Milestone
from server.model.issue import Issue
from server.schema.issue import (
    CreateIssueSchema,
    QueryIssueSchema,
    GiteeIssueQueryV8,
)
from server.apps.issue.handler import (
    GiteeV8IssueHandler,
    GiteeV8BaseIssueHandler,
)


def get_issue_tag():
    return {
        "name": "issue",
        "description": "issue相关接口",
    }


class IssueEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IssueEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "创建issue",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CreateIssueSchema,
    })
    def post(self, body: CreateIssueSchema):
        return GiteeV8IssueHandler.create_issue(body=body)

    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IssueEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "分页查询issue",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryIssueSchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: QueryIssueSchema):
        return GiteeV8IssueHandler.get_issues(query=query)


class IssueItemEvent(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IssueItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "issue详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, issue_id):
        _issue = Issue.query.filter_by(id=issue_id).first()
        if _issue:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=_issue.to_dict()
            )
        else:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="issue does not exist.",
            )


class GiteeIssuesItem(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeIssuesItem",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "gitee平台issue详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, gitee_issue_id):
        return GiteeV8BaseIssueHandler().get(gitee_issue_id)


class GiteeIssuesType(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeIssuesType",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "当前用户所属组织的issue类型(gitee平台redis缓存数据)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryBaseModel
    })
    def get(self, query: QueryBaseModel):
        return GiteeV8IssueHandler.get_issue_type(query.org_id)


class GiteeIssuesState(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeIssuesState",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "当前用户所属组织的issue状态(gitee平台redis缓存数据)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return GiteeV8IssueHandler.get_issue_state()


class GiteeProjectEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeProjectEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "当前用户所属组织的所有项目(gitee平台redis缓存数据)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        data = GiteeV8BaseIssueHandler().get_all_project()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )


class GiteeIssuesV8(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeIssuesV8",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "通过里程碑id查询所有gitee平台issue数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GiteeIssueQueryV8
    })
    def get(self, query: GiteeIssueQueryV8):
        milestone = Milestone.query.filter_by(id=query.milestone_id).first()
        if not milestone or milestone.is_sync is False:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={}
            )
        _body = query.__dict__
        _body.update(
            {
                "milestone_id": milestone.gitee_milestone_id,
            }
        )
        return GiteeV8BaseIssueHandler(org_id=query.org_id).get_all(_body)


class UpdateGiteeIssuesTypeState(Resource):
    @auth.login_required
    @swagger_adapt.api_schema_model_map({
        "__module__": get_issue_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UpdateGiteeIssuesTypeState",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_issue_tag(),  # 当前接口所对应的标签
        "summary": "同步更新issue的类型、状态数据至redis",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        from server.model.organization import Organization
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None,
            Organization.enterprise_token is not None,
        ).all()
        for _org in orgs:
            isa = GiteeV8BaseIssueHandler(org_id=_org.id)
            _resp = isa.get_issue_types()
            resp = _resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_types = json.loads(
                    resp.get("data")).get("data")
                t_issue_types = []
                for _type in issue_types:
                    t_issue_types.append(
                        {
                            "id": _type.get("id"),
                            "title": _type.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_types(_org.enterprise_id),
                    {"data": json.dumps(t_issue_types)}
                )
            else:
                return _resp
            _resp = isa.get_issue_states()
            resp = _resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_states = json.loads(
                    resp.get("data")
                ).get("data")

                t_issue_states = []
                for _state in issue_states:
                    t_issue_states.append(
                        {
                            "id": _state.get("id"),
                            "title": _state.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_states(_org.enterprise_id),
                    {"data": json.dumps(t_issue_states)}
                )
            else:
                return _resp
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )
