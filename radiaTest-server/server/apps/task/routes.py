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

from flask import g, jsonify
from flask_restful import Resource
from flask_pydantic import validate
from server import socketio, casbin_enforcer, swagger_adapt
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET, workspace_error_collect
from server.schema.base import PageBaseSchema
from server.schema.task import (
    AddTaskSchema,
    AddTaskStatusSchema,
    UpdateTaskStatusSchema,
    UpdateTaskStatusOrderSchema,
    AddTaskSchema,
    OutAddTaskSchema,
    QueryTaskSchema,
    UpdateTaskExecutorSchema,
    UpdateTaskSchema,
    UpdateTaskParticipantSchema,
    AddTaskCommentSchema,
    DelTaskCommentSchema,
    AddTaskTagSchema,
    DelTaskTagSchema,
    AddFamilyMemberSchema,
    QueryFamilySchema,
    DelFamilyMemberSchema,
    TaskReportContentSchema,
    QueryTaskCaseSchema,
    AddTaskCaseSchema,
    DelTaskCaseSchema,
    QueryTaskStatisticsSchema,
    TaskJobResultSchema,
    TaskCaseResultSchema,
    DistributeTaskCaseSchema,
    DistributeTemplateTypeSchema,
    DistributeTemplate,
    DeleteTaskList,
    MilestoneTaskSchema,
    UpdateTaskPercentageSchema,
    QueryTaskByTimeSchema,
)
from server.apps.task.handlers import (
    HandlerTaskStatus,
    HandlerTask,
    HandlerTaskParticipant,
    HandlerTaskComment,
    HandlerTaskTag,
    HandlerTaskFamily,
    HandlerTaskCase,
    HandlerTaskReport,
    HandlerTaskProgress,
    HandlerTaskMilestone,
    HandlerTaskStatistics,
    HandlerTaskExecute,
    HandlerCaseTask,
    HandlerCaseFrame,
)
from server.apps.task.template_handler import (
    HandlerTemplate,
    HandlerTemplateType,
    HandlerTaskDistributeCass
)


def get_task_tag():
    return {
        "name": "task任务",
        "description": "task任务相关接口",
    }


class Status(Resource):

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Status",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取task任务状态",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return HandlerTaskStatus.get()

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Status",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "添加task任务状态",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddTaskStatusSchema
    })
    def post(self, body: AddTaskStatusSchema):
        return HandlerTaskStatus.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Status",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑task任务状态",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskStatusSchema
    })
    def put(self, status_id, body: UpdateTaskStatusSchema):
        return HandlerTaskStatus.update(status_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Status",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除task任务状态",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, status_id):
        return HandlerTaskStatus.delete(status_id)


class StatusOrder(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "StatusOrder",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "调整task任务状态排序",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskStatusOrderSchema
    })
    def put(self, body: UpdateTaskStatusOrderSchema):
        return HandlerTaskStatus.update_order(body)


class Task(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Task",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "分页查询task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryTaskSchema
    })
    def get(self, workspace: str, query: QueryTaskSchema):
        return HandlerTask.get_all(query, workspace)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Task",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "创建task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddTaskSchema
    })
    def post(self, body: AddTaskSchema):
        return HandlerTask.create(body)


class TaskItem(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskItem",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "task任务详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, task_id: int):
        return HandlerTask.get(task_id)

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskItem",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, task_id):
        return HandlerTask.delete(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskItem",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskSchema
    })
    def put(self, task_id, body: UpdateTaskSchema):
        return HandlerTask.update(task_id, body)


class TaskGantt(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskGantt",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "task任务甘特图",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryTaskByTimeSchema
    })
    def get(self, query: QueryTaskByTimeSchema):
        return HandlerTask.get_all_gantt_tasks(query)


class TaskPercentage(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskPercentage",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "变更task任务百分比",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskPercentageSchema
    })
    def put(self, task_id, body: UpdateTaskPercentageSchema):
        return HandlerTask.update_percentage(task_id, body.percentage)


class ParticipantItem(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ParticipantItem",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务的协助者信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, task_id):
        return HandlerTaskParticipant.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ParticipantItem",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑任务的协助者信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskParticipantSchema
    })
    def put(self, task_id, body: UpdateTaskParticipantSchema):
        return HandlerTaskParticipant.update(task_id, body)


class Participants(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Participants",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取当前组织中的所有协助者",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskParticipantSchema
    })
    def get(self):
        return HandlerTaskParticipant.get(None, query_task=True)


class ExecutorItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ExecutorItem",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑任务的执行人(责任人)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateTaskExecutorSchema
    })
    def put(self, task_id, body: UpdateTaskExecutorSchema):
        return HandlerTask.update_executor(task_id, body)


class Comment(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Comment",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务评论",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, task_id):
        return HandlerTaskComment.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Comment",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除任务评论",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, task_id, body: DelTaskCommentSchema):
        return HandlerTaskComment.delete(task_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Comment",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "添加任务评论",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddTaskCommentSchema
    })
    def post(self, task_id, body: AddTaskCommentSchema):
        return HandlerTaskComment.add(task_id, body)


class RecycleBin(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RecycleBin",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "分页获取回收站中的任务列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PageBaseSchema
    })
    def get(self, query: PageBaseSchema):
        return HandlerTask.get_recycle_bin(query)


class Tag(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Tag",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取所有的任务标签",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return HandlerTaskTag.get()

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Tag",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "创建任务标签",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddTaskTagSchema
    })
    def post(self, body: AddTaskTagSchema):
        return HandlerTaskTag.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Tag",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除任务标签",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DelTaskTagSchema
    })
    def delete(self, body: DelTaskTagSchema):
        return HandlerTaskTag.delete(body)


class FamilyItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FamilyItem",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务的关联任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryFamilySchema
    })
    def get(self, task_id, query: QueryFamilySchema):
        return HandlerTaskFamily.get(task_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FamilyItem",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "关联任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddFamilyMemberSchema
    })
    def post(self, task_id, body: AddFamilyMemberSchema):
        return HandlerTaskFamily.add(task_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FamilyItem",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "取消关联任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DelFamilyMemberSchema
    })
    def delete(self, task_id, body: DelFamilyMemberSchema):
        return HandlerTaskFamily.delete(task_id, body)


class Family(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Family",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务的关联任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return HandlerTaskFamily.get(None, None)


class Report(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Report",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, task_id):
        return HandlerTaskReport.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Report",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑任务报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": TaskReportContentSchema
    })
    def put(self, task_id, body: TaskReportContentSchema):
        return HandlerTaskReport.update(task_id, body)


class Cases(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Cases",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务的关联用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryTaskCaseSchema
    })
    def get(self, task_id, query: QueryTaskCaseSchema):
        return HandlerTaskCase.get(task_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Cases",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "任务关联用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AddTaskCaseSchema
    })
    def post(self, task_id, milestone_id, body: AddTaskCaseSchema):
        return HandlerTaskCase.add(task_id, milestone_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Cases",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "任务取消用例关联",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DelTaskCaseSchema
    })
    def delete(self, task_id, milestone_id, body: DelTaskCaseSchema):
        return HandlerTaskCase.delete(task_id, milestone_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Cases",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "子任务任务关联用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DistributeTaskCaseSchema
    })
    def put(self, task_id, milestone_id, body: DistributeTaskCaseSchema):
        return HandlerTaskCase.distribute(task_id, milestone_id, body)


class CasesResult(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "CasesResult",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, task_id):
        return HandlerTaskCase.task_cases_result(task_id)


class TaskStatistics(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskStatistics",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务统计结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryTaskStatisticsSchema
    })
    def get(self, query: QueryTaskStatisticsSchema):
        return HandlerTaskStatistics(query).run()


class TaskMilestones(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskMilestones",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "变更job任务结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": TaskJobResultSchema
    })
    def put(self, taskmilestone_id: int, body: TaskJobResultSchema):
        return HandlerTaskMilestone.update_task_process(taskmilestone_id, body)


class TaskMilestonesCases(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskMilestonesCases",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "变更task手工用例结果",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": TaskCaseResultSchema
    })
    def put(self, task_id: int, taskmilestone_id: int, case_id: int, body: TaskCaseResultSchema):
        return HandlerTaskMilestone.update_manual_cases_result(task_id, taskmilestone_id, case_id, body)


class TaskExecute(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskExecute",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "外部任务创建接口",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": OutAddTaskSchema
    })
    def post(self, body: OutAddTaskSchema):
        e = HandlerTaskExecute().create(body)
        if not isinstance(e, HandlerTaskExecute):
            return e
        return e.execute()


class TaskDistributeTemplate(Resource):

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskDistributeTemplate",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取任务分发模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DistributeTemplate.Query
    })
    def get(self, query: DistributeTemplate.Query):
        return HandlerTemplate.get(query)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskDistributeTemplate",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "添加任务分发模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DistributeTemplate.Add
    })
    def post(self, body: DistributeTemplate.Add):
        return HandlerTemplate.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskDistributeTemplate",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑任务分发模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DistributeTemplate.Update
    })
    def put(self, template_id, body: DistributeTemplate.Update):
        return HandlerTemplate.update(template_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskDistributeTemplate",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除任务分发模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, template_id):
        return HandlerTemplate.delete(template_id)


class DistributeType(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "DistributeType",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "分页获取task任务模板所有用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DistributeTemplateTypeSchema.Query
    })
    def get(self, query: DistributeTemplateTypeSchema.Query):
        return HandlerTemplateType.get(query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "DistributeType",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "创建task任务模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DistributeTemplateTypeSchema.Add
    })
    def post(self, template_id, body: DistributeTemplateTypeSchema.Add):
        return HandlerTemplateType.add(template_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "DistributeType",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "编辑task任务模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DistributeTemplateTypeSchema.Update
    })
    def put(self, type_id, body: DistributeTemplateTypeSchema.Update):
        return HandlerTemplateType.update(type_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "DistributeType",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除ask任务模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, type_id):
        return HandlerTemplateType.delete(type_id)


class DistributeCaseByTemplate(Resource):

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "DistributeCaseByTemplate",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "通过模板分发用例任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DistributeTemplate.Distribute
    })
    def put(self, task_id, template_id, body: DistributeTemplate.Distribute):
        return HandlerTaskDistributeCass().distribute(task_id, template_id, body.__dict__)


class TaskList(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskList",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "删除task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DeleteTaskList
    })
    def put(self, body: DeleteTaskList):
        return HandlerTask.delete_task_list(body)


class CaseTask(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "CaseTask",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "查看task用例任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, case_id):
        return HandlerCaseTask.get_task_info(case_id)


class TaskFrame(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TaskFrame",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取task所有架构",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return HandlerCaseFrame.get_task_frame()


class MileStoneTask(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MileStoneTask",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取里程碑task任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MilestoneTaskSchema
    })
    def get(self, milestone_id, query: MilestoneTaskSchema):
        return HandlerTask.get_milestone_tasks(milestone_id, query)


class MilestoneTaskProgress(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MilestoneTaskProgress",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取版本任务测试进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id):
        try:
            taskprogress = HandlerTaskProgress(milestone_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        return taskprogress.get_task_test_progress()


class CaseNodeTaskProgress(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "CaseNodeTaskProgress",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取用例和测试进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id, case_node_id):
        try:
            taskprogress = HandlerTaskProgress(milestone_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        return taskprogress.get_task_case_node_and_test_progress(case_node_id)


class SubTaskProgress(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "SubTaskProgress",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_task_tag(),  # 当前接口所对应的标签
        "summary": "获取task子任务测试进展",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id, task_id):
        try:
            taskprogress = HandlerTaskProgress(milestone_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        return taskprogress.get_test_progress_by_task(task_id)

