from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model import Milestone
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.milestone import GiteeIssueQueryV8, MilestoneBaseSchema, MilestoneCreateSchema, MilestoneQuerySchema, MilestoneUpdateSchema
from .handler import MilestoneOpenApiHandler, IssueOpenApiHandlerV5, IssueOpenApiHandlerV8, MilestoneHandler


class MilestoneItemEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, milestone_id):
        return Delete(Milestone, {"id":milestone_id}).single(Milestone, '/milestone')

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: MilestoneUpdateSchema):
        return Edit(Milestone, body.__dict__).single(Milestone, '/milestone')

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, milestone_id):
        return Select(Milestone, {"id":milestone_id}).single()


class MilestoneEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: MilestoneCreateSchema):
        return Insert(Milestone, body.__dict__).single(Milestone, '/milestone')

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: MilestoneBaseSchema):
        params = dict()
        q_dict = query.__dict__
        for key in q_dict.keys():
            if q_dict[key] is not None:
                params[key] = q_dict[key]

        return Select(Milestone, params).fuzz()


class MilestoneEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: MilestoneCreateSchema):
        if body.is_sync:
            return MilestoneOpenApiHandler(body.__dict__).create()
        else:
            return Insert(
                Milestone, 
                body.__dict__
            ).single(Milestone, '/milestone')

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: MilestoneQuerySchema):
        return MilestoneHandler.get_all(query)


class MilestoneItemEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, milestone_id, body: MilestoneUpdateSchema):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exitst".format(milestone_id)
            )

        if milestone.is_sync is True:
            return MilestoneOpenApiHandler(body.__dict__).edit(milestone_id)
        else:
            _body = body.__dict__
            _body.update({
                "id": milestone_id
            })

            if _body.get("state_event"):
                state_event = _body.pop("state_event")
                if state_event == "activate":
                    _body.update({
                        "state": "active"
                    })
                else:
                    _body.update({
                        "state": "closed"
                    })

            return Edit(Milestone, _body).single(Milestone, '/milestone')
    
    @auth.login_required()
    @response_collect
    def delete(self, milestone_id):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exitst".format(milestone_id)
            )

        if milestone.is_sync is True:
            return MilestoneOpenApiHandler().delete(milestone_id)
        else:
            return Delete(
                Milestone, 
                {"id":milestone_id}
            ).single(Milestone, '/milestone')


class MilestoneItemChangeStateV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, milestone_id, body: MilestoneUpdateSchema):
        return MilestoneOpenApiHandler(body.__dict__).change_state(milestone_id)


class MilestonePreciseEvent(Resource):
    @auth.login_required()
    @validate()
    def get(self, query: MilestoneBaseSchema):
        return Select(Milestone, query.__dict__).precise()


class GiteeIssuesV1(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self):
        _issues = IssueOpenApiHandlerV5(
            request.args.get("enterprise"),
            request.args.get("milestone")
        )

        return _issues.getAll(request.args)


class GiteeIssuesV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: GiteeIssueQueryV8):
        return IssueOpenApiHandlerV8().get_all(query.__dict__)


class GiteeIssuesTypeV2(Resource):
    @auth.login_required
    def get(self):
        return IssueOpenApiHandlerV8().get_issue_types()