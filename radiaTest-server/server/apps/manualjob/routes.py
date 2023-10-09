# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author : 董霖峰
# @email : 1063183942@qq.com
# @Date : 2022/12/11 05:22:35
# @License : Mulan PSL v2
#####################################
# 手工测试任务(ManualJob)相关接口的route层

from flask import jsonify
from flask_pydantic import validate
from flask_restful import Resource

from server import swagger_adapt
from server.apps.manualjob.handler import (
    ManualJobHandler,
    ManualJobSubmitHandler,
    ManualJobLogHandler,
    ManualJobDeleteHandler,
    ManualJobLogQueryHandler,
    ManualJobGroupCopyHandler
)
from server.model.manualjob import ManualJob, ManualJobGroup
from server.model.testcase import Case
from server.model.milestone import Milestone
from server.schema.manualjob import (
    ManualJobCreate,
    ManualJobQuery,
    ManualJobLogModify,
    ManualJobLogDelete,
    ManualJobGroupQuery,
    ManualJobGroupStatus,
    ManualJobGroupReport,
    ManualJobModify,
    ManualJobGroupCopySchema
)
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET, workspace_error_collect


def get_manual_job_tag():
    return {
        "name": "手工任务",
        "description": "手工任务接口",
    }


# 若任务组已完成，则上锁不允许用户进行操作
def manual_job_operate_lock(manual_job_id):
    manual_job = ManualJob.query.get(manual_job_id)
    if manual_job.job_group_id:
        # 按id查找ManualJobGroup
        manual_job_group = ManualJobGroup.query.get(manual_job.job_group_id)
        if manual_job_group.status == 1:
            return False
    return True


class ManualJobEvent(Resource):
    """
        添加、查询ManualJob
        url="/api/v1/manual-job", methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "创建手工任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobCreate,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: ManualJobCreate):
        """
            在数据库中新增ManualJob数据, 根据其所属的Case的步骤数, 在数据库中新增数个ManualJobStep.
            请求体:
            {
                "case_id": int,
                "name": str,
                "executor_id": int,
                "milestone_id": int
            }
            返回体:
            {
                "data": {
                "id": int
                },
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        try:
            _ = map(int, body.cases.split(','))
        except ValueError:
            return jsonify(error_code=RET.PARMA_ERR, error_msg="cases param error.")
        _milestone = Milestone.query.get(body.milestone_id)
        if _milestone is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the milestone with id {body.milestone_id} does not exist"
            )
        _manual_job_group = ManualJobGroup.query.filter_by(name=body.name).all()
        if _manual_job_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"任务名重复，请修改后重试！"
            )

        return ManualJobHandler.create(body)

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "分页查询手工任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ManualJobQuery
    })
    def get(self, workspace: str, query: ManualJobQuery):
        """
            请求行示例: /api/v1/manual-job?status=0&page_num=1&page_size=1
            page_num默认为1, page_size默认为10.
            返回体:
            {
                "data": {
                    "items": [
                        {
                            "id": int,
                            "name": str,
                            "case_id": int,
                            "milestone_name": str,
                            "executor_name": str,
                            "create_time": datetime,
                            "update_time": datetime,
                            "current_step": int,
                            "total_step": int,
                            "result": str,
                            "status": int,
                            "start_time": datetime,
                            "end_time": datetime,
                        }
                    ],
                    "current_page": int,
                    "has_next": boolean,
                    "has_prev": boolean,
                    "page_size": int,
                    "pages": int,
                    "next_num": int,
                    "prev_num": int,
                    "total": int
                },
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        if query.case_id is not None:
            _case = Case.query.get(query.case_id)
            if _case is None:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"the case with id {query.case_id} does not exist"
                )
        return ManualJobHandler.query(query, workspace)


class ManualJobSubmitEvent(Resource):
    """
        提交完成执行指定id的手工测试任务(ManualJob)
        url="/api/v1/manual-job/<int:manual_job_id>/submit", methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobSubmitEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "设置手工任务状态已结束(每个步骤都有日志, 且日志的passed字段都是True,"
                   " 则把此手工测试任务的result字段更改为1(与预期一致))",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, manual_job_id: int):
        """
            设置指定id的手工测试任务(ManualJob)的status字段为1(已结束), 设置end_time字段为当前时间.
            如果该手工测试任务的每个步骤都有日志, 且日志的passed字段都是True, 则把此手工测试任务的result字段更改为1(与预期一致).
            请求参数: 无
            返回体示例:
            {
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        if manual_job_operate_lock(manual_job_id) is False:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=f"该任务已被锁定，请将状态改为执行中后再进行该操作！"
            )
        manual_job = ManualJob.query.get(manual_job_id)
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job with id {manual_job_id} does not exist"
            )
        else:
            return ManualJobSubmitHandler.post(manual_job)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobSubmitEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "设置手工任务结果",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobModify
    })
    def put(self, manual_job_id: int, body: ManualJobModify):
        if manual_job_operate_lock(manual_job_id) is False:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=f"该任务已被锁定，请将状态改为执行中后再进行该操作！"
            )
        manual_job = ManualJob.query.get(manual_job_id)
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job with id {manual_job_id} does not exist"
            )
        else:
            return ManualJobSubmitHandler.update(manual_job, body)


class ManualJobLogEvent(Resource):
    """
        更新、删除指定id的手工测试任务(ManualJob)的日志.
        url="/api/v1/manual-job/log/<int:manual_job_id>", methods=["PUT", "DELETE"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobLogEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "更新指定id的手工测试任务(ManualJob)的日志",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobLogModify
    })
    def put(self, manual_job_id, body: ManualJobLogModify):
        """
            更新指定id的手工测试任务(ManualJob)的日志. 同时把这个ManualJob的current_step字段置为这个步骤的序数.
            请求行: /api/v1/manual-job/log/<int:manual_job_id>
            请求体: step指更新这个ManualJob第几个步骤的日志.
            {
                "step": int,
                "log_content": html_str,
                "passed": booleean
            }
            返回体示例:
            {
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        if manual_job_operate_lock(manual_job_id) is False:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=f"该任务已被锁定，请将状态改为执行中后再进行该操作！"
            )
        return ManualJobLogHandler.update(manual_job_id, body)
    
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobLogEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "删除指定id的手工测试任务(ManualJob)的日志",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ManualJobLogModify
    })
    def delete(self, manual_job_id, body: ManualJobLogDelete):
        """
            删除指定id的手工测试任务(ManualJob)的日志. 同时, 这个ManualJob的current_step字段退回到它剩下的ManualJobStep中step_num字段的最大值.
            请求行: /api/v1/manual-job/log/<int:manual_job_id>
            请求体: step指更新这个ManualJob第几个步骤的日志. 如果留空则删除该ManualJob所有日志, 该ManualJob的current_step字段归零.
            {
                "step": int
            }
            返回体:
            {
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        if manual_job_operate_lock(manual_job_id) is False:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=f"该任务已被锁定，请将状态改为执行中后再进行该操作！"
            )
        return ManualJobLogHandler.delete(manual_job_id, body)


class ManualJobDeleteEvent(Resource):
    """
        删除指定id的手工测试任务(ManualJob)
        url="/api/v1/manual-job/<int:manual_job_id>", methods=["DELETE"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobDeleteEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "删除指定id的手工测试任务",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, manual_job_id: int):
        """
            在数据库中删除指定id的手工测试任务(ManualJob)
            请求行:api/v1/manual-job/<int:manual_job_id>
            返回体:
            {
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        if manual_job_operate_lock(manual_job_id) is False:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=f"该任务已被锁定，请将状态改为执行中后再进行该操作！"
            )
        return ManualJobDeleteHandler.delete(manual_job_id)


class ManualJobLogQueryEvent(Resource):
    """
        查询指定id的手工测试任务(ManualJob)的指定步骤的日志.
        url="/api/v1/manual-job/<int:manual_job_id>/step/<int:step_num>", methods=["GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobLogQueryEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "获取指定手工测试任务下的指定步骤的日志",
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, manual_job_id: int, step_num: int):
        """
            请求行: /api/v1/manual-job/<int:manual_job_id>/step/<int:step_num>
            请求行中manual_job_id和step_num分别代表要查询手工测试任务(ManualJob)的id, 查询它第几步的日志.
            返回体:
            {
                "data": {
                    "operation": str,
                    "content": html_str,
                    "passed": boolean
                },
                "error_code": 2000,
                "error_msg": "Request processed successfully."
            }
        """
        # 按id查找ManualJob
        manual_job = ManualJob.query.get(manual_job_id)
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job with id {manual_job_id} does not exist"
            )
        return ManualJobLogQueryHandler.query(manual_job, step_num)


class ManualJobGroupEvent(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobGroupEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "分页查询手工任务组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ManualJobGroupQuery
    })
    def get(self, workspace: str, query: ManualJobGroupQuery):
        return ManualJobHandler.query_manual_job_group(query, workspace)


class ManualJobGroupDetail(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobGroupDetail",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "手工任务组详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, manual_job_group_id):
        # 按id查找ManualJobGroup
        manual_job_group = ManualJobGroup.query.get(manual_job_group_id)
        if manual_job_group is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job_group with id {manual_job_group_id} does not exist"
            )
        return jsonify(
            data=manual_job_group.to_statist(),
            error_code=RET.OK,
            error_msg="Request processed successfully."
            )

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobGroupDetail",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "手工任务组状态变更",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobGroupStatus
    })
    def put(self, manual_job_group_id, body: ManualJobGroupStatus):
        # 按id查找ManualJobGroup
        manual_job_group = ManualJobGroup.query.get(manual_job_group_id)
        if manual_job_group is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job_group with id {manual_job_group_id} does not exist"
            )
        if manual_job_group.status == body.status:
            return jsonify(
                        error_code=RET.DATA_EXIST_ERR,
                        error_msg="任务状态已经变更，无需重复操作"
                    )

        manual_job_group.status = body.status
        manual_job_group.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobGroupDetail",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "手工任务组报告上传",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobGroupReport
    })
    def post(self, manual_job_group_id, body: ManualJobGroupReport):
        # 按id查找ManualJobGroup
        manual_job_group = ManualJobGroup.query.get(manual_job_group_id)
        if manual_job_group is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job_group with id {manual_job_group_id} does not exist"
            )

        manual_job_group.report = body.report
        manual_job_group.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully."
        )

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ManualJobGroupDetail",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "手工任务组删除",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, manual_job_group_id):
        return ManualJobDeleteHandler.delete_manual_job_group(manual_job_group_id)


class ManualJobGroupCopy(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_manual_job_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ManualJobGroupCopy",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_manual_job_tag(),  # 当前接口所对应的标签
        "summary": "复制手工任务组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ManualJobGroupCopySchema
    })
    def post(self, body: ManualJobGroupCopySchema):
        # 按id查找ManualJobGroup
        manual_job_group = ManualJobGroup.query.get(body.id)
        if manual_job_group is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job_group with id {body.id} does not exist"
            )
        return ManualJobGroupCopyHandler.copy(manual_job_group, body.__dict__)
