import json
from flask import request, jsonify, render_template, make_response, current_app
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.model.milestone import Milestone, IssueSolvedRate, TestReport
from server.utils.db import Edit, Select
from server.schema.milestone import (
    GiteeIssueQueryV8,
    MilestoneBaseSchema,
    MilestoneCreateSchema,
    MilestoneQuerySchema,
    MilestoneUpdateSchema,
    IssueQuerySchema,
    GiteeMilestoneQuerySchema,
    SyncMilestoneSchema,
    MilestoneStateEventSchema,
    IssueRateFieldSchema,
    GenerateTestReport,
    QueryTestReportFile,
)
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer
from .handler import (
    IssueStatisticsHandlerV8,
    MilestoneOpenApiHandler,
    IssueOpenApiHandlerV5,
    IssueOpenApiHandlerV8,
    MilestoneHandler,
    CreateMilestone,
    DeleteMilestone,
    IssueHandlerV8,
)



class OrgMilestoneEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, org_id, query: MilestoneQuerySchema):
        filter_params = [
            Milestone.org_id == org_id
        ]
        return MilestoneHandler.get_milestone(query, filter_params)


class GroupMilestoneEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, group_id, query: MilestoneQuerySchema):
        filter_params = [
            Milestone.group_id == group_id
        ]
        return MilestoneHandler.get_milestone(query, filter_params)


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
        filter_params = GetAllByPermission(Milestone).get_filter()
        return MilestoneHandler.get_milestone(query, filter_params)


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
                _data["start_time"] = _data.get(
                    "start_time").strftime("%Y-%m-%d")
            if _data.get("end_time"):
                _data["end_time"] = _data.get("end_time").strftime("%Y-%m-%d")
            return MilestoneOpenApiHandler(_data).edit(milestone.gitee_milestone_id)
        else:
            _body = body.__dict__
            _body.update({"id": milestone_id})

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
        return IssueOpenApiHandlerV8().get_all(_body)


class GenerateTestReportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, milestone_id, query: GenerateTestReport):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )
        return IssueHandlerV8().generate_update_test_report(milestone_id, query.uri)


class TestReportFileEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, milestone_id, query: QueryTestReportFile):
        _test_report = TestReport.query.filter_by(milestone_id=milestone_id).first()
        if not _test_report:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no test report.",
            )

        tmp_folder = current_app.template_folder
        current_app.template_folder = current_app.config.get("TEST_REPORT_PATH")
        if query.file_type == "md":
            resp =  make_response(render_template(_test_report.md_file))
        else:
            resp = make_response(render_template(_test_report.html_file))
        current_app.template_folder = tmp_folder
        return resp


class TestReportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, milestone_id):
        _test_report = TestReport.query.filter_by(milestone_id=milestone_id).first()
        if not _test_report:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="no test report.",
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_test_report.to_json()
        )


class GiteeIssuesItemV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, issue_id):
        return IssueOpenApiHandlerV8().get(issue_id)


class GiteeIssuesTypeV2(Resource):
    @auth.login_required
    def get(self):
        return IssueStatisticsHandlerV8.get_issue_type()


class GiteeIssuesStateV2(Resource):
    @auth.login_required
    def get(self):
        return IssueStatisticsHandlerV8.get_issue_state()


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


class UpdateMilestoneIssueRateByField(Resource):
    @auth.login_required
    @validate()
    def put(self, milestone_id, body: IssueRateFieldSchema):
        return IssueStatisticsHandlerV8.update_milestone_issue_rate_by_field(milestone_id, body.field)


class UpdateGiteeIssuesTypeState(Resource):
    @auth.login_required
    def post(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        from server.model.organization import Organization
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None).all()
        for _org in orgs:
            gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_org.id)
            if gitee_id:
                isa = IssueOpenApiHandlerV8(gitee_id=gitee_id)
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
                        {"data": t_issue_types}
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
                        {"data": t_issue_states}
                    )
                else:
                    return _resp
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class GiteeMilestoneEventV2(Resource):
    @auth.login_required
    @validate()
    def get(self, query: GiteeMilestoneQuerySchema):
        return MilestoneOpenApiHandler().get_milestones(params=query.__dict__)


class SyncMilestoneItemEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, milestone_id, body: SyncMilestoneSchema):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )

        milestone.gitee_milestone_id = body.gitee_milestone_id
        milestone.is_sync = True
        milestone.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class MilestoneItemStateEventV2(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, milestone_id, body: MilestoneStateEventSchema):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )
        _body = body.__dict__
        if _body.get("state_event"):
            state_event = _body.pop("state_event")
            if state_event == "activate":
                _body.update({"state": "active"})
            else:
                _body.update({"state": "closed"})

        if milestone.state == _body.get("state"):
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="State event cannot transition when {}".format(
                    milestone.state),
            )

        if milestone.is_sync is True:
            return MilestoneOpenApiHandler(body.__dict__).edit_state_event(milestone.gitee_milestone_id)

        milestone.state = _body.get("state")
        milestone.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK.")
