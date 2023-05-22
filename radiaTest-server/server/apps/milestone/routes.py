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

from flask import jsonify, render_template, make_response, current_app, g
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET, workspace_error_collect
from server.model.milestone import Milestone, TestReport
from server.utils.db import Select
from server.schema.milestone import (
    MilestoneBaseSchema,
    MilestoneCreateSchema,
    MilestoneQuerySchema,
    MilestoneUpdateSchema,
    GiteeMilestoneQuerySchema,
    SyncMilestoneSchema,
    MilestoneStateEventSchema,
    GenerateTestReport,
    QueryTestReportFile,
    QueryMilestoneByTimeSchema,
)
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer
from server.apps.milestone.handler import (
    IssueStatisticsHandlerV8,
    MilestoneOpenApiHandler,
    MilestoneHandler,
    CreateMilestone,
    DeleteMilestone,
    GenerateVersionTestReport,
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
    @workspace_error_collect
    @validate()
    def get(self, workspace: str, query: MilestoneQuerySchema):
        filter_params = GetAllByPermission(Milestone, workspace).get_filter()
        return MilestoneHandler.get_milestone(query, filter_params)


class MilestoneGantt(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: QueryMilestoneByTimeSchema):
        return MilestoneHandler.get_all_gantt_milestones(query=query)


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
        if int(g.gitee_id) != int(milestone.creator_id):
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="you have no right to change the milestone {}".format(milestone.name),
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
            for key, value in _body.items():
                if value is not None:
                    setattr(milestone, key, value)
            milestone.add_update(Milestone, "/milestone")
            return jsonify(
                error_code=RET.OK,
                error_msg="OK."
            )

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
    @response_collect
    @validate()
    def get(self, query: MilestoneBaseSchema):
        return GetAllByPermission(Milestone).precise(query.__dict__)


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
        return GenerateVersionTestReport().generate_update_test_report(milestone_id, query.uri)


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


class UpdateGiteeIssuesStatistics(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        return IssueStatisticsHandlerV8.update_issue_rate()


class MilestoneIssueRateEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, milestone_id):
        return IssueStatisticsHandlerV8.update_milestone_issue_rate(milestone_id)

    @auth.login_required
    @response_collect
    @validate()
    def get(self, milestone_id):
        return IssueStatisticsHandlerV8.get_rate_by_milestone(milestone_id)


class GiteeMilestoneEventV2(Resource):
    @auth.login_required
    @response_collect
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
        milestone.add_update(Milestone, "/milestone")

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
