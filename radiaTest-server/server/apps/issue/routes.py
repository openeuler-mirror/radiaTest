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
from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

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
    IssueOpenApiHandlerV5,
)


class IssueEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CreateIssueSchema):
        return GiteeV8IssueHandler.create_issue(body=body)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: QueryIssueSchema):
        return GiteeV8IssueHandler.get_issues(query=query)


class IssueItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, gitee_issue_id):
        return GiteeV8BaseIssueHandler().get(gitee_issue_id)


class GiteeIssuesType(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        return GiteeV8IssueHandler.get_issue_type()


class GiteeIssuesState(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        return GiteeV8IssueHandler.get_issue_state()


class GiteeIssuesV5(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self):
        _issues = IssueOpenApiHandlerV5(
            request.args.get("enterprise"), request.args.get("milestone")
        )

        return _issues.get_all(request.args)


class GiteeProjectEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self):
        data =  GiteeV8BaseIssueHandler().get_all_project()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )


class GiteeIssuesV8(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
        return GiteeV8BaseIssueHandler().get_all(_body)


class UpdateGiteeIssuesTypeState(Resource):
    @auth.login_required
    def post(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        from server.model.organization import Organization
        from server.apps.milestone.handler import IssueStatisticsHandlerV8
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None).all()
        for _org in orgs:
            gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_org.id)
            if gitee_id:
                isa = GiteeV8BaseIssueHandler(gitee_id=gitee_id)
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
