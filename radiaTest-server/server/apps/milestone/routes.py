from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model.milestone import Milestone, IssueSolvedRate
from server.utils.db import Edit, Select
from server.schema.milestone import (
    GiteeIssueQueryV8,
    MilestoneBaseSchema,
    MilestoneCreateSchema,
    MilestoneQuerySchema,
    MilestoneUpdateSchema,
    IssueQuerySchema,
)
from .handler import (
    IssueStatisticsHandlerV8,
    MilestoneOpenApiHandler,
    IssueOpenApiHandlerV5,
    IssueOpenApiHandlerV8,
    MilestoneHandler,
    CreateMilestone,
    DeleteMilestone,
)
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer


class MilestoneEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: MilestoneCreateSchema):
        return CreateMilestone.run(body.__dict__)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: MilestoneQuerySchema):
        return MilestoneHandler.get_all(query)


class MilestoneItemEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, milestone_id, body: MilestoneUpdateSchema):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )

        if milestone.is_sync is True:
            _data = body.__dict__
            if _data.get("start_time"):
                _data["start_time"] = _data.get("start_time").strftime("%Y-%m-%d")
            if _data.get("end_time"):
                _data["end_time"] = _data.get("end_time").strftime("%Y-%m-%d")
            return MilestoneOpenApiHandler(_data).edit(milestone_id)
        else:
            _body = body.__dict__
            _body.update({"id": milestone_id})

            if _body.get("state_event"):
                state_event = _body.pop("state_event")
                if state_event == "activate":
                    _body.update({"state": "active"})
                else:
                    _body.update({"state": "closed"})

            return Edit(Milestone, _body).single(Milestone, "/milestone")

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def delete(self, milestone_id):
        return DeleteMilestone.single(milestone_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def get(self, milestone_id):
        return Select(Milestone, {"id": milestone_id}).single()


class MilestonePreciseEvent(Resource):
    @auth.login_required()
    @validate()
    def get(self, query: MilestoneBaseSchema):
        return GetAllByPermission(Milestone).precise(query.__dict__)


class GiteeIssuesV1(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self):
        _issues = IssueOpenApiHandlerV5(
            request.args.get("enterprise"), request.args.get("milestone")
        )

        return _issues.getAll(request.args)


class GiteeIssuesV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: GiteeIssueQueryV8):
        return IssueOpenApiHandlerV8().get_all(query.__dict__)


class GiteeIssuesItemV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, issue_id):
        return IssueOpenApiHandlerV8().get(issue_id)


class GiteeIssuesTypeV2(Resource):
    @auth.login_required
    def get(self):
        return IssueOpenApiHandlerV8().get_issue_types()


class GiteeIssuesStatisticsByMilestone(Resource):
    @auth.login_required
    @validate()
    def get(self, milestone_id, query: IssueQuerySchema):
        if query.is_live:
            return IssueStatisticsHandlerV8.get_rate_by_milestone(milestone_id)
        else:
            return IssueStatisticsHandlerV8.get_rate_by_milestone2(milestone_id)


class UpdateGiteeIssuesStatistics(Resource):
    @auth.login_required
    def get(self):
        return IssueStatisticsHandlerV8.update_issue_rate()
