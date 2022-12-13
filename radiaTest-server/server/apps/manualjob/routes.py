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

from server import db
from server.apps.manualjob.handler import (
    ManualJobHandler,
    ManualJobSubmitHandler,
    ManualJobLogHandler,
    ManualJobDeleteHandler,
    ManualJobLogQueryHandler)
from server.model.manualjob import ManualJob
from server.model.testcase import Case
from server.schema.manualjob import (
    ManualJobCreate,
    ManualJobQuery,
    ManualJobLogModify,
    ManualJobLogDelete
)
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET


def _find_object_by_id(id_value: int, table: db.Model):
    """
        按请求参数中的id到数据库中查询记录, 如果查到了就返回反映此条记录的对象, 否则返回None.
    """
    obj = table.query.filter_by(id=id_value).first()  # 这里把id写死了
    return obj


class ManualJobEvent(Resource):
    """
        添加、查询ManualJob
        url="/api/v1/manual-job", methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        # 查case表, 看输入的case_id是否存在, 不存在就返回错误信息
        input_case_id = body.case_id
        _case = _find_object_by_id(input_case_id, Case)
        if _case is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the case with id {input_case_id} does not exist"
            )
        return ManualJobHandler.create(_case, body)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: ManualJobQuery):
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
        return ManualJobHandler.query(query)


class ManualJobSubmitEvent(Resource):
    """
        提交完成执行指定id的手工测试任务(ManualJob)
        url="/api/v1/manual-job/<int:manual_job_id>/submit", methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        manual_job = _find_object_by_id(manual_job_id, ManualJob)
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the manual_job with id {manual_job_id} does not exist"
            )
        else:
            return ManualJobSubmitHandler.post(manual_job)


class ManualJobLogEvent(Resource):
    """
        更新、删除指定id的手工测试任务(ManualJob)的日志.
        url="/api/v1/manual-job/log/<int:manual_job_id>", methods=["PUT", "DELETE"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        return ManualJobLogHandler.update(manual_job_id, body)
    
    @auth.login_required()
    @response_collect
    @validate()
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
        return ManualJobLogHandler.delete(manual_job_id, body)


class ManualJobDeleteEvent(Resource):
    """
        删除指定id的手工测试任务(ManualJob)
        url="/api/v1/manual-job/<int:manual_job_id>", methods=["DELETE"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        return ManualJobDeleteHandler.delete(manual_job_id)


class ManualJobLogQueryEvent(Resource):
    """
        查询指定id的手工测试任务(ManualJob)的指定步骤的日志.
        url="/api/v1/manual-job/<int:manual_job_id>/step/<int:step_num>", methods=["GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        manual_job = _find_object_by_id(manual_job_id, ManualJob)
        if manual_job is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"manual_job with id {manual_job_id} does not exist"
            )
        return ManualJobLogQueryHandler.query(manual_job, step_num)
