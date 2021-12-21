# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 10:24:25
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.model import Milestone
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.base import DeleteBaseModel
from server.schema.milestone import MilestoneBase, MilestoneUpdate
from .handler import HandlerIssuesList


class MilestoneEvent(Resource):
    @validate()
    def post(self, body: MilestoneBase):
        return Insert(Milestone, body.__dict__).single(Milestone, '/milestone')

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Milestone, body.__dict__).batch(Milestone, '/milestone')

    @validate()
    def put(self, body: MilestoneUpdate):
        return Edit(Milestone, body.__dict__).single(Milestone, '/milestone')

    def get(self):
        body = request.args.to_dict()
        return Select(Milestone, body).fuzz()


class PreciseGet(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(Milestone, body).precise()


class GiteeIssues(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self):
        _issues = HandlerIssuesList(
            request.args.get("enterprise"),
            request.args.get("milestone")
        )

        return _issues.getAll(request.args)