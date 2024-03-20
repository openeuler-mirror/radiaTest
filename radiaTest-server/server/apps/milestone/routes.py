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

from flask import jsonify, render_template, make_response, current_app, g, request
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
    BatchSyncMilestoneSchema
)
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer, swagger_adapt
from server.apps.milestone.handler import (
    IssueStatisticsHandlerV8,
    MilestoneOpenApiHandler,
    MilestoneHandler,
    CreateMilestone,
    DeleteMilestone,
    GenerateVersionTestReport,
)


def get_milestone_tag():
    return {
        "name": "里程碑",
        "description": "里程碑相关接口",
    }


class OrgMilestoneEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "OrgMilestoneEventV1",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "组织下的里程碑分页查询",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MilestoneQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, org_id, query: MilestoneQuerySchema):
        filter_params = [
            Milestone.org_id == org_id
        ]
        return MilestoneHandler.get_milestone(query, filter_params)


class GroupMilestoneEventV1(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GroupMilestoneEventV1",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "用户组下的里程碑分页查询",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MilestoneQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, group_id, query: MilestoneQuerySchema):
        filter_params = [
            Milestone.group_id == group_id
        ]
        return MilestoneHandler.get_milestone(query, filter_params)


class MilestoneEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneEventV2",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "里程碑创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": MilestoneCreateSchema,
    })
    def post(self, body: MilestoneCreateSchema):
        return CreateMilestone.run(body.__dict__)

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneEventV2",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "workspace下的里程碑分页查询",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MilestoneQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, workspace: str, query: MilestoneQuerySchema):

        filter_params = GetAllByPermission(Milestone, workspace, query.org_id).get_filter()
        return MilestoneHandler.get_milestone(query, filter_params)


class MilestoneGantt(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneGantt",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "获取里程碑列表gantt",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryMilestoneByTimeSchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: QueryMilestoneByTimeSchema):
        return MilestoneHandler.get_all_gantt_milestones(query=query)


class MilestoneItemEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneItemEventV2",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "更新里程碑",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": MilestoneUpdateSchema
    })
    def put(self, milestone_id, body: MilestoneUpdateSchema):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )
        if g.user_id != milestone.creator_id:
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneItemEventV2",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "删除里程碑",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, milestone_id):
        return DeleteMilestone.single(milestone_id)

    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneItemEventV2",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "里程碑详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id):
        return Select(Milestone, {"id": milestone_id}).single()


class MilestonePreciseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestonePreciseEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "查询里程碑",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MilestoneBaseSchema
    })
    def get(self, query: MilestoneBaseSchema):
        return GetAllByPermission(Milestone).precise(query.__dict__)


class GenerateTestReportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GenerateTestReportEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "生成update测试报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GenerateTestReport
    })
    def get(self, milestone_id, query: GenerateTestReport):
        milestone = Milestone.query.filter_by(id=milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone {} not exist".format(milestone_id),
            )
        return GenerateVersionTestReport().generate_update_test_report(milestone_id)


class TestReportFileEvent(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TestReportFileEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "下载指定类型的里程碑测试报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryTestReportFile
    })
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
            resp = make_response(render_template(_test_report.md_file))
        else:
            resp = make_response(render_template(_test_report.html_file))
        current_app.template_folder = tmp_folder
        return resp


class TestReportEvent(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TestReportEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "获取指定里程碑的测试报告信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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


class MilestoneIssueRateEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneIssueRateEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "更新指定里程碑的问题解决率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, milestone_id):
        return IssueStatisticsHandlerV8.update_milestone_issue_rate(milestone_id)

    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneIssueRateEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "获取指定里程碑的问题解决率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id):
        return IssueStatisticsHandlerV8.get_rate_by_milestone(milestone_id)


class GiteeMilestoneEventV2(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GiteeMilestoneEventV2",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "分页查询gitee里程碑",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": GiteeMilestoneQuerySchema
    })
    def get(self, query: GiteeMilestoneQuerySchema):
        return MilestoneOpenApiHandler().get_milestones(params=query.__dict__)


class SyncMilestoneItemEventV2(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "SyncMilestoneItemEventV2",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "同步gitee里程碑id至平台",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": SyncMilestoneSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneItemStateEventV2",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "同步平台里程碑状态，若is_sync为true则同时同步至gitee",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": MilestoneStateEventSchema
    })
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


class MilestoneGiteeIds(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneGiteeIds",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "获取当前产品关联的所有gitee里程碑id",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_id):
        return jsonify(error_code=RET.OK, error_msg="OK", data=CreateMilestone.gitee_milestone_id_list(product_id))


class BatchSyncGiteeMilestone(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BatchSyncGiteeMilestone",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "批量同步gitee里程碑至平台",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": BatchSyncMilestoneSchema
    })
    def post(self, body: BatchSyncMilestoneSchema):
        return CreateMilestone().batch_sync_create(body.__dict__)


class VerifyMilestoneName(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_milestone_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VerifyMilestoneName",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_milestone_tag(),  # 当前接口所对应的标签
        "summary": "校验里程碑名称是否存在",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": [{
            "name": "name",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "里程碑名称",
            "schema": {"type": "string"}}],
    })
    def get(self):
        request.args.get("name")
        return jsonify(error_code=RET.OK, error_msg="OK",
                       data=CreateMilestone.verify_milestone_name(request.args.get("name")))
