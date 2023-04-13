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
from server import socketio, casbin_enforcer
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
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


class Status(Resource):

    @auth.login_required()
    @response_collect
    def get(self):
        return HandlerTaskStatus.get()

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def post(self, body: AddTaskStatusSchema):
        return HandlerTaskStatus.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, status_id, body: UpdateTaskStatusSchema):
        return HandlerTaskStatus.update(status_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, status_id):
        return HandlerTaskStatus.delete(status_id)


class StatusOrder(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, body: UpdateTaskStatusOrderSchema):
        return HandlerTaskStatus.update_order(body)


class Task(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: QueryTaskSchema):
        return HandlerTask.get_all(g.user_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: AddTaskSchema):
        return HandlerTask.create(body)


class TaskItem(Resource):
    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self, task_id: int):
        return HandlerTask.get(task_id)

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def delete(self, task_id):
        return HandlerTask.delete(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, body: UpdateTaskSchema):
        return HandlerTask.update(task_id, body)


class ParticipantItem(Resource):
    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self, task_id):
        return HandlerTaskParticipant.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, body: UpdateTaskParticipantSchema):
        return HandlerTaskParticipant.update(task_id, body)


class Participants(Resource):
    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self):
        return HandlerTaskParticipant.get(None, query_task=True)


class ExecutorItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, body: UpdateTaskExecutorSchema):
        return HandlerTask.update_executor(task_id, body)


class Comment(Resource):
    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self, task_id):
        return HandlerTaskComment.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, task_id, body: DelTaskCommentSchema):
        return HandlerTaskComment.delete(task_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, task_id, body: AddTaskCommentSchema):
        return HandlerTaskComment.add(task_id, body)


class RecycleBin(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: PageBaseSchema):
        return HandlerTask.get_recycle_bin(query)


class Tag(Resource):
    @auth.login_required()
    @response_collect
    def get(self):
        return HandlerTaskTag.get()

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: AddTaskTagSchema):
        return HandlerTaskTag.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, body: DelTaskTagSchema):
        return HandlerTaskTag.delete(body)


class FamilyItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    # @casbin_enforcer.enforcer
    def get(self, task_id, query: QueryFamilySchema):
        return HandlerTaskFamily.get(task_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def post(self, task_id, body: AddFamilyMemberSchema):
        return HandlerTaskFamily.add(task_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, task_id, body: DelFamilyMemberSchema):
        return HandlerTaskFamily.delete(task_id, body)


class Family(Resource):
    @auth.login_required()
    @response_collect
    def get(self):
        return HandlerTaskFamily.get(None, None)


class Report(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    # @casbin_enforcer.enforcer
    def get(self, task_id):
        return HandlerTaskReport.get(task_id)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, body: TaskReportContentSchema):
        return HandlerTaskReport.update(task_id, body)


class Cases(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    # @casbin_enforcer.enforcer
    def get(self, task_id, query: QueryTaskCaseSchema):
        return HandlerTaskCase.get(task_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def post(self, task_id, milestone_id, body: AddTaskCaseSchema):
        return HandlerTaskCase.add(task_id, milestone_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, task_id, milestone_id, body: DelTaskCaseSchema):
        return HandlerTaskCase.delete(task_id, milestone_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, milestone_id, body: DistributeTaskCaseSchema):
        return HandlerTaskCase.distribute(task_id, milestone_id, body)


class CasesResult(Resource):
    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self, task_id):
        return HandlerTaskCase.task_cases_result(task_id)


class TaskStatistics(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: QueryTaskStatisticsSchema):
        return HandlerTaskStatistics(query).run()


class TaskMilestones(Resource):
    @validate()
    def put(self, taskmilestone_id: int, body: TaskJobResultSchema):
        return HandlerTaskMilestone.update_task_process(taskmilestone_id, body)


class TaskMilestonesCases(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id: int, taskmilestone_id: int, case_id: int, body: TaskCaseResultSchema):
        return HandlerTaskMilestone.update_manual_cases_result(task_id, taskmilestone_id, case_id, body)


class TaskExecute(Resource):
    @validate()
    def post(self, body: OutAddTaskSchema):
        e = HandlerTaskExecute().create(body)
        if not isinstance(e, HandlerTaskExecute):
            return e
        return e.execute()


class TaskDistributeTemplate(Resource):

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: DistributeTemplate.Query):
        return HandlerTemplate.get(query)

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: DistributeTemplate.Add):
        return HandlerTemplate.add(body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, template_id, body: DistributeTemplate.Update):
        return HandlerTemplate.update(template_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, template_id):
        return HandlerTemplate.delete(template_id)


class DistributeType(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: DistributeTemplateTypeSchema.Query):
        return HandlerTemplateType.get(query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def post(self, template_id, body: DistributeTemplateTypeSchema.Add):
        return HandlerTemplateType.add(template_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, type_id, body: DistributeTemplateTypeSchema.Update):
        return HandlerTemplateType.update(type_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, type_id):
        return HandlerTemplateType.delete(type_id)


class DistributeCaseByTemplate(Resource):

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, task_id, template_id, body: DistributeTemplate.Distribute):
        return HandlerTaskDistributeCass().distribute(task_id, template_id, body)


class TaskList(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: DeleteTaskList):
        return HandlerTask.delete_task_list(body)


class CaseTask(Resource):
    @auth.login_required()
    @response_collect
    def get(self, case_id):
        return HandlerCaseTask.get_task_info(case_id)


class TaskFrame(Resource):
    @auth.login_required()
    @response_collect
    def get(self):
        return HandlerCaseFrame.get_task_frame()


class MileStoneTask(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, milestone_id, query: MilestoneTaskSchema):
        return HandlerTask.get_milestone_tasks(milestone_id, query)


class MilestoneTaskProgress(Resource):
    @auth.login_required()
    @response_collect
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
    def get(self, milestone_id, task_id):
        try:
            taskprogress = HandlerTaskProgress(milestone_id)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e),
            )
        return taskprogress.get_test_progress_by_task(task_id)

