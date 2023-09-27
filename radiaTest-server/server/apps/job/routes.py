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

import re

from sqlalchemy import or_, and_
from flask import jsonify, request, g
from flask_restful import Resource
from flask_pydantic import validate

from server import redis_client, swagger_adapt
from server.utils.redis_util import RedisKey
from server.model.job import Analyzed, Job, job_family, Logs
from server.utils.db import Edit, Select, Insert, collect_sql_error
from server.utils.permission_utils import GetAllByPermission
from server.schema.job import (
    AnalyzedCreateSchema,
    AnalyzedQueryBase,
    AnalyzedQueryItem,
    AnalyzedQueryRecords,
    AnalyzedUpdateItem,
    JobCreateSchema,
    JobUpdateSchema,
    LogCreateSchema,
    RunSuiteBase,
    RunTemplateBase,
    JobQuerySchema,
)
from server.model.testcase import Case, Baseline, CaseNode
from server.model.pmachine import MachineGroup
from server.model.task import TaskMilestone
from server.model.template import Template
from server.utils.auth_util import auth
from server.utils.page_util import PageUtil
from server.utils.response_util import RET, response_collect, workspace_error_collect
from .handlers import JobMessenger


def get_job_tag():
    return {
        "name": "job任务",
        "description": "job任务相关接口",
    }


class RunSuiteEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RunSuiteEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "执行任务接口，仅做转发向messenger发起请求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RunSuiteBase,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: RunSuiteBase):
        machine_group = MachineGroup.query.filter_by(id=body.machine_group_id).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="invalid machine group"
            )

        messenger = JobMessenger(body.__dict__)

        return messenger.send_job(machine_group, "/api/v1/job/suite")


class RunTemplateEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "RunTemplateEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "执行模板任务接口，仅做转发向messenger发起请求",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RunTemplateBase,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: RunTemplateBase):
        template = Template.query.get(body.template_id)
        if template is None:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="template doesn't exist."
            )
        _body = body.__dict__
        _body['template_name'] = template.template_name
        _body['permission_type'] = template.permission_type
        _body['group_id'] = template.group_id
        _body['org_id'] = template.org_id
        _body['creator_id'] = g.user_id
        messenger = JobMessenger(_body)

        machine_group = MachineGroup.query.filter_by(id=body.machine_group_id).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="invalid machine group"
            )

        return messenger.send_job(machine_group, "/api/v1/job/template")


class JobEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "JobEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "分页查询job",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": JobQuerySchema
    })
    def get(self, workspace: str, query: JobQuerySchema):
        filter_params = GetAllByPermission(Job, workspace).get_filter()

        filter_params.append(
            or_(
                Job.multiple.is_(True),
                and_(
                    Job.is_suite_job.is_(True),
                    Job.multiple.is_(False),
                )
            )
        )

        if query.name:
            filter_params.append(Job.name.like(f"%{query.name}%"))

        if query.status == "PENDING":
            filter_params.append(Job.status == "PENDING")
        elif query.status == "DONE":
            filter_params.append(
                or_(
                    Job.status == "DONE", 
                    Job.status == "BLOCK"
                )
            )
        else:
            filter_params.append(
                and_(
                    Job.status != "DONE",
                    Job.status != "BLOCK",
                    Job.status != "PENDING"
                )
            )

        query_filter = Job.query.outerjoin(
            job_family, 
            Job.id == job_family.c.parent_id
        ).filter(*filter_params)

        if query.sorted_by == "create_time":
            query_filter = query_filter.order_by(Job.create_time.desc(), Job.id.asc())
        elif query.sorted_by == "end_time":
            query_filter = query_filter.order_by(Job.end_time.desc(), Job.id.asc())

        return PageUtil.get_data(query_filter, query)

    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "JobEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "创建job",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": JobCreateSchema
    })
    def post(self, workspace: str, body: JobCreateSchema):
        _body = body.__dict__
        _permission_body = {
            "permission_type": "org",
            "org_id": int(
                redis_client.hget(
                    RedisKey.user(g.user_id), 
                    "current_org_id"
                )
            ),
            "creator_id": g.user_id
        }

        if re.match(r'^group_\d+$', workspace):
            _permission_body.update({
                "permission_type": "group",
                "group_id": int(workspace.split("_")[1])
            })

        _body.update(_permission_body)

        parent = None
        if _body.get("parent_id"):
            parent = Job.query.filter_by(id=_body.pop("parent_id")).first()

        job = Insert(Job, _body).insert_obj()

        if parent is not None:
            job.parent.append(parent)
        
        job.add_update(Job, "/job")

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=job.to_json()
        )


class JobItemEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "JobItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "job详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="job is not exist"
            )
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=job.to_json(),
        )
    
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "JobItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "更新job",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": JobUpdateSchema
    })
    def put(self, job_id, body: JobUpdateSchema):
        _body = body.__dict__
        _body.update({"id": job_id})
        return Edit(Job, _body).single(Job, "/job")


class JobItemChildren(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "JobItemChildren",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "获取job所有子任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="job is not exist")
        
        data = [child.to_json() for child in job.children]

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data,
        )


class AnalyzedEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "获取job所有分析数据(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AnalyzedQueryBase
    })
    def get(self, query: AnalyzedQueryBase):
        return_data = []

        job = Job.query.filter_by(id=query.job_id).first()
        if not job:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="the job not exist"
            )

        if job.multiple is True:
            for child in job.children:
                _analyzeds = child.analyzeds
                return_data += [_analyzed.to_json() for _analyzed in _analyzeds]
        else:
            _analyzeds = job.analyzeds
            return_data = [_analyzed.to_json() for _analyzed in _analyzeds]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)
    
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "创建分析数据(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AnalyzedCreateSchema
    })
    def post(self, body: AnalyzedCreateSchema):
        case_node = CaseNode.query.join(TaskMilestone).join(Baseline).filter(
            TaskMilestone.job_id == body.job_id,
            Baseline.milestone_id == TaskMilestone.milestone_id,
            CaseNode.baseline_id == Baseline.id,
            CaseNode.case_id == body.case_id,
        ).first()
        case_node.case_result = body.result
        case_node.add_update()

        return Insert(Analyzed, body.__dict__).single(Analyzed, "/analyzed")


class AnalyzedItemEvent(Resource):
    @auth.login_required
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "查询分析数据(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AnalyzedQueryItem
    })
    def get(self, analyzed_id, query: AnalyzedQueryItem):
        body = query.__dict__
        body.update({"id": analyzed_id})
        return Select(Analyzed, body).precise()

    @auth.login_required
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "同步日志记录到分析数据(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AnalyzedUpdateItem
    })
    def put(self, analyzed_id, body: AnalyzedUpdateItem):
        analyzed = Analyzed.query.filter_by(id=analyzed_id).first()
        if not analyzed:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the anlayzed does not exist",
            )
        
        if body.fail_type:
            analyzed.fail_type = body.fail_type
        if body.details:
            analyzed.details = body.details
        
        if body.logs:
            for log_id in body.logs:
                log = Logs.query.filter_by(id=log_id).first()
                if not log:
                    continue
                analyzed.logs.append(log)
        
        analyzed.add_update(Analyzed, "/analyzed", True)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


class AnalyzedRecords(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedRecords",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "通过用例id查询所有分析数据(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AnalyzedQueryRecords
    })
    def get(self, query: AnalyzedQueryRecords):
        _case = Case.query.filter_by(id=query.case_id).first()

        if not _case:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="case is not exist"
            )

        return Select(Analyzed, {"case_id": _case.id}).precise()


class PreciseAnalyzedEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PreciseAnalyzedEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "查询分析数据列表(执行记录)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        body = request.args.to_dict()
        return Select(Analyzed, body).precise()


class AnalyzedLogs(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "AnalyzedLogs",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "获取分析数据(执行记录)详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, analyzed_id):
        _analyzed = Analyzed.query.filter_by(id=analyzed_id).first()
        return jsonify(
            error_code=RET.OK, 
            error_msg="OK", 
            data=_analyzed.get_logs()
        )


class LogEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_job_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "LogEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_job_tag(),  # 当前接口所对应的标签
        "summary": "日志创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": LogCreateSchema
    })
    def post(self, body: LogCreateSchema):
        log = Insert(Logs, body.__dict__).insert_obj()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=log.to_json(),
        )
