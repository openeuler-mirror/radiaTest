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

from datetime import datetime, timedelta
import json
import math
import ast
import os
import parser
import pytz
from celery import current_app

from flask import jsonify, g, request, Response
from sqlalchemy import or_

from server import db, redis_client
from server.model.task import TaskStatus, Task, TaskParticipant, TaskComment
from server.model.task import TaskTag, TaskReportContent, TaskMilestone, TaskManualCase
from server.model.group import ReUserGroup, GroupRole, Group
from server.model.job import Job, Analyzed
from server.model.user import User
from server.model.organization import Organization
from server.model.milestone import Milestone
from server.model.testcase import Case, CaseNode
from server.model.permission import Role
from server.schema.task import (
    UpdateTaskExecutorSchema,
    AddTaskSchema,
    EnumsTaskExecutorType,
    UpdateTaskStatusOrderSchema,
    UpdateTaskSchema,
    AddTaskCaseSchema,
    TaskBaseSchema,
    TaskInfoSchema,
    TagInfoSchema,
    PageBaseSchema,
    TaskCaseResultSchema,
    TaskRecycleBinInfo,
    DeleteTaskList,
    AddTaskTagSchema,
    DelTaskCaseSchema,
    DelTaskTagSchema,
    DelFamilyMemberSchema,
    AddFamilyMemberSchema,
    QueryFamilySchema,
    TaskReportContentSchema,
    QueryTaskCaseSchema,
    DistributeTaskCaseSchema,
    TaskJobResultSchema,
    QueryTaskStatisticsSchema,
    OutAddTaskSchema,
)
from server.schema import Frame
from server.schema.issue import GiteeIssueQueryV8
from server.schema.user import UserBaseSchema
from server.schema.group import GroupInfoSchema
from server.utils.db import collect_sql_error, Insert, Delete
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.read_from_yaml import get_api
from server.utils.permission_utils import PermissionManager, GetAllByPermission
from server.apps.issue.handler import GiteeV8BaseIssueHandler
from .services import (
    UpdateTaskStatusService,
    get_family_member,
    update_task_display,
    AnalysisTaskInfo,
    send_message,
    judge_task_automatic,
)
from server.apps.testcase.handler import CaseNodeHandler


base_dir = os.path.dirname(os.path.abspath(__file__))


class HandlerTaskStatus(object):
    @staticmethod
    @collect_sql_error
    def get():
        statuses = TaskStatus.query.order_by(TaskStatus.order).all()
        status_names = [item.name for item in statuses]
        insert_names = [
            item
            for item in ["待办中", "进行中", "执行中", "已执行", "已完成"]
            if item not in status_names
        ]
        order = statuses[-1].order if statuses else 1
        for name in insert_names:
            order += 1
            Insert(TaskStatus, data={"name": name, "order": order}).insert_id()
        if len(insert_names) > 0:
            statuses = TaskStatus.query.order_by(TaskStatus.order).all()

        return_data = [status.to_dict() for status in statuses]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def add(body):
        status = TaskStatus.query.order_by(
            TaskStatus.order.desc(), TaskStatus.id.asc()
        ).first()
        new_order = (status.order + 1) if status else 1
        status = TaskStatus(name=body.name, order=new_order, creator_id=g.user_id)
        status.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(status_id, body):
        status = TaskStatus.query.get(status_id)
        if not status:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="data no find")
        if status.name in ["待办中", "进行中", "执行中", "已执行", "已完成"]:
            return jsonify(error_code=RET.PARMA_ERR, error_msg="The state is locked")
        status.name = body.name
        status.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(status_id):
        status = TaskStatus.query.get(status_id)
        if not status:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="data no find")
        if status.tasks:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="data has exist")
        if status.name in ["待办中", "进行中", "执行中", "已执行", "已完成"]:
            return jsonify(error_code=RET.PARMA_ERR, error_msg="The state is locked")
        db.session.delete(status)
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update_order(body: UpdateTaskStatusOrderSchema):
        body.order_list.sort(key=lambda x: x.order)
        execute_index = executed_index = -1
        for item in body.order_list:
            if item.name == "执行中":
                execute_index = body.order_list.index(item)
            elif item.name == "已执行":
                executed_index = body.order_list.index(item)
        if (
            execute_index >= 0
            and executed_index >= 0
            and executed_index - execute_index != 1
        ):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg='The states ["执行中", "已执行"] order is locked',
            )
        for item in body.order_list:
            TaskStatus.query.filter_by(name=item.name).update(
                {"order": item.order}, synchronize_session=False
            )
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTask(object):
    @staticmethod
    @collect_sql_error
    def create(body: AddTaskSchema):
        """新建任务"""
        task = Task.query.filter_by(title=body.title).first()
        if task:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="task has exist")

        insert_dict = body.dict()
        insert_dict["creator_id"] = g.user_id
        insert_dict["org_id"] = redis_client.hget(
            RedisKey.user(g.user_id), "current_org_id"
        )
        current_org_id = int(
            redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        )
        case_ids = []
        if body.milestone_id:
            case_node = CaseNode.query.filter_by(
                milestone_id=body.milestone_id,
                in_set=False,
                is_root=True,
                type="baseline",
            ).first()
            if not case_node:
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg="version baseline associated with milestone does not exist",
                )

            if current_org_id != case_node.org_id:
                return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to query")

            task = Task.query.filter(
                Task.case_node_id == case_node.id,
                Task.type == "VERSION",
                Task.is_delete.is_(False),
            ).first()
            if task:
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg=f"current test strategy has already associated with task {task.title}",
                )
            insert_dict["test_strategy"] = True
            insert_dict["case_node_id"] = case_node.id
            case_ids, _ = CaseNodeHandler.get_all_case(case_node.id)
            if len(case_ids) == 0:
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg=f"version baseline {case_node.title} test cases do not exist",
                )
        executor_id = body.executor_id
        insert_dict["permission_type"] = (
            body.type.lower() if body.type in ["PERSON", "GROUP"] else "org"
        )

        if body.executor_type == EnumsTaskExecutorType.GROUP.value and (
            body.type == "ORGANIZATION" or body.type == "VERSION"
        ):
            insert_dict["group_id"] = executor_id
            relationship = ReUserGroup.query.filter_by(
                group_id=executor_id,
                is_delete=False,
                role_type=GroupRole.create_user.value,
            ).first()
            if not relationship:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="group is not exists"
                )
            executor_id = relationship.user.user_id
        insert_dict["executor_id"] = executor_id
        task = Task()
        for key, value in insert_dict.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        if body.child_id:
            children = Task.query.filter(Task.id.in_(body.child_id)).all()
            _ = [task.children.append(item) for item in children]
            Task.query.filter(Task.id.in_(body.child_id)).update(
                {"display": False}, synchronize_session=False
            )
            db.session.commit()

        if body.parent_id:
            parents = Task.query.filter(Task.id.in_(body.parent_id)).all()
            _ = [task.parents.append(item) for item in parents]
            task.display = False
        task.add_update()

        if case_ids and body.milestone_id:
            task = Task.query.filter_by(title=body.title).first()
            task.milestones.append(
                TaskMilestone(task_id=task.id, milestone_id=body.milestone_id)
            )
            update_task_schema = UpdateTaskSchema(milestone_id=body.milestone_id)
            HandlerTask.update(task.id, update_task_schema)
            add_task_case_schema = AddTaskCaseSchema(case_id=case_ids)
            HandlerTaskCase.add(task.id, body.milestone_id, add_task_case_schema)
        pm = PermissionManager()
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "task.yaml"), task.id
        )
        _data = {
            "permission_type": task.permission_type,
            "org_id": task.org_id,
            "group_id": task.group_id,
        }
        pm.generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data,
        )
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "execute_task.yaml"), task.id
        )
        if body.executor_type == EnumsTaskExecutorType.GROUP.value:
            _data = {
                "permission_type": "group",
                "group_id": task.group_id,
            }
            pm.bind_scope_nouser(
                scope_datas_allow=scope_data_allow,
                scope_datas_deny=scope_data_deny,
                _data=_data,
            )
        else:
            if int(task.creator_id) != int(executor_id):
                pm.bind_scope_user(
                    scope_datas_allow=scope_data_allow,
                    scope_datas_deny=scope_data_deny,
                    user_id=executor_id,
                )

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get_all(user_id, query, workspace=None):
        """获取任务列表"""
        join_params = []
        filter_params = GetAllByPermission(Task, workspace).get_filter()
        for key, value in query.dict().items():
            if not value and key != "is_delete":
                continue
            if key == "title":
                filter_params.append(Task.title.like(f"%{value}%"))
            elif key == "participant_id":
                join_params.append(TaskParticipant)
                filter_params.append(TaskParticipant.participant_id.in_(value))
            elif key == "start_time":
                filter_params.append(Task.start_time >= value)
            elif key == "deadline":
                filter_params.append(Task.deadline <= value)
            elif key == "milestone_id":
                join_params.append(TaskMilestone)
                filter_params.append(TaskMilestone.milestone_id.in_(value))
            elif hasattr(Task, key):
                filter_params.append(getattr(Task, key) == value)

        if join_params:
            query_filter = Task.query.join(*join_params).filter(*filter_params)
        else:
            query_filter = Task.query.filter(*filter_params)

        def page_func(item):
            item_dict = TaskBaseSchema(**item.__dict__).dict()
            creator = User.query.get(item.creator_id)
            item_dict["creator"] = UserBaseSchema(**creator.__dict__).dict()
            executor = User.query.get(item.executor_id)
            item_dict["executor"] = UserBaseSchema(**executor.__dict__).dict()
            item_dict["has_milestone"] = True if item.milestones else False
            item_dict["status"] = item.task_status.to_dict()
            item_dict["has_auto_case"] = False
            for milestone in item.milestones:
                if len(milestone.cases) > len(milestone.manual_cases):
                    item_dict["has_auto_case"] = True
                    break
            item_dict["auto_case_success"] = True
            for milestone in item.milestones:
                if (
                    len(milestone.cases) > len(milestone.manual_cases)
                    and milestone.job_result != "done"
                ):
                    item_dict["auto_case_success"] = False
                    break
            return item_dict

        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
            func=page_func
        )

    @staticmethod
    @collect_sql_error
    def delete(task_id):
        task = Task.query.filter_by(id=task_id, is_delete=True).first()
        if not task:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="task is not exists")
        for attr_key in ["participants", "comments", "milestones"]:
            attr = getattr(task, attr_key)
            if attr_key == "milestones":
                for milestone in task.milestones:
                    _ = [db.session.delete(item) for item in milestone.manual_cases]
                    db.session.commit()
            if attr:
                _ = [db.session.delete(item) for item in attr]
                db.session.commit()

            _ = [task.children.remove(item) for item in task.children.all()]
            task.add_update()
            _ = [task.parents.remove(item) for item in task.parents.all()]
            task.add_update()
        if task.report:
            db.session.delete(task.report)
            db.session.commit()
        db.session.delete(task)
        db.session.commit()
        PermissionManager().clean("/api/v1/tasks/", [task_id])
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    def update_executor(task_id, body: UpdateTaskExecutorSchema):
        task = Task.query.get(task_id)
        if not task:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="task does not exist")
        if task.task_status.name == "已完成":
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="task has accomplished, not allowed edit !",
            )
  
        if body.executor_type == EnumsTaskExecutorType.PERSON.value:
            user = User.query.filter_by(user_id=body.executor_id).first()
            if not user:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="user is not exists"
                )
        else:
            relationship = ReUserGroup.query.filter_by(
                is_delete=False,
                org_id=task.org_id,
                group_id=body.executor_id,
                role_type=GroupRole.create_user.value,
            ).first()
            if not relationship:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="group is not exists"
                )
        
        participant = TaskParticipant.query.filter_by(
            task_id=task.id,
            participant_id=body.executor_id,
            type=body.executor_type,
        ).first()
        if participant:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="the user has been a participant.",
            )

        old_executor_type = task.executor_type
        old_executor_id = task.executor_id

        pm = PermissionManager()
        if old_executor_type == EnumsTaskExecutorType.GROUP.value:
            if body.executor_type == EnumsTaskExecutorType.GROUP.value:
                if int(old_executor_id) != int(body.executor_id):
                    role = Role.query.filter_by(
                        name="admin", type="group", group_id=task.group_id
                    ).first()
                    scope_data_allow, scope_data_deny = pm.get_api_list(
                        "task", os.path.join(base_dir, "execute_task.yaml"), task.id
                    )
                    PermissionManager.unbind_scope_role(
                        scope_data_allow,
                        False,
                        role.id,
                    )
                    relationship = ReUserGroup.query.filter_by(
                        group_id=body.executor_id,
                        is_delete=False,
                        role_type=GroupRole.create_user.value,
                    ).first()
                    if not relationship:
                        return jsonify(
                            error_code=RET.NO_DATA_ERR, error_msg="group is not exists"
                        )
                    task.executor_id = relationship.user.user_id
                    task.group_id = relationship.group.id
                    task.executor_type = body.executor_type
                    _data = {
                        "permission_type": "group",
                        "org_id": task.org_id,
                        "group_id": task.group_id,
                    }
                    pm.bind_scope_nouser(
                        scope_datas_allow=scope_data_allow,
                        scope_datas_deny=scope_data_deny,
                        _data=_data,
                    )
            else:
                
                role = Role.query.filter_by(
                    name="admin", type="group", group_id=task.group_id
                ).first()
                scope_data_allow, scope_data_deny = pm.get_api_list(
                    "task", os.path.join(base_dir, "execute_task.yaml"), task.id
                )
                PermissionManager.unbind_scope_role(
                    scope_data_allow,
                    False,
                    role.id,
                )
                task.executor_id = body.executor_id
                task.executor_type = body.executor_type
                if int(task.creator_id) != int(task.executor_id):
                    pm.bind_scope_user(
                        scope_datas_allow=scope_data_allow,
                        scope_datas_deny=scope_data_deny,
                        user_id=task.executor_id,
                    )
        else:
            if body.executor_type == EnumsTaskExecutorType.GROUP.value:
                scope_data_allow, scope_data_deny = pm.get_api_list(
                    "task", os.path.join(base_dir, "execute_task.yaml"), task.id
                )

                relationship = ReUserGroup.query.filter_by(
                    group_id=body.executor_id,
                    is_delete=False,
                    role_type=GroupRole.create_user.value,
                ).first()
                if not relationship:
                    return jsonify(
                        error_code=RET.NO_DATA_ERR, error_msg="group is not exists"
                    )

                if int(task.creator_id) != int(old_executor_id):
                    role = Role.query.filter_by(name=old_executor_id).first()
                    PermissionManager.unbind_scope_role(
                        scope_data_allow,
                        False,
                        role.id,
                    )

                task.executor_id = relationship.user.user_id
                task.group_id = relationship.group.id
                task.executor_type = body.executor_type
                _data = {
                    "permission_type": "group",
                    "org_id": task.org_id,
                    "group_id": task.group_id,
                }
                pm.bind_scope_nouser(
                    scope_datas_allow=scope_data_allow,
                    scope_datas_deny=scope_data_deny,
                    _data=_data,
                )
            else:
                if int(body.executor_id) != int(old_executor_id):
                    task.executor_id = body.executor_id
                    scope_data_allow, scope_data_deny = pm.get_api_list(
                        "task", os.path.join(base_dir, "execute_task.yaml"), task.id
                    )

                    if int(task.creator_id) != int(old_executor_id):
                        role = Role.query.filter_by(name=old_executor_id).first()
                        PermissionManager.unbind_scope_role(
                            scope_data_allow,
                            False,
                            role.id,
                        )
                    if int(task.creator_id) != int(body.executor_id):
                        pm.bind_scope_user(
                            scope_datas_allow=scope_data_allow,
                            scope_datas_deny=scope_data_deny,
                            user_id=task.executor_id,
                        )
        task.add_update()
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(task_id, body: UpdateTaskSchema):
        task = Task.query.get(task_id)
        if not task:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="task does not exist")
        if task.task_status.name == "已完成":
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="task has accomplished, not allowed edit !",
            )
        for key, value in body.dict().items():
            if key in ["milestones", "frame", "status_id", "status_name"]:
                continue
            elif (value or value is False) and hasattr(task, key):
                setattr(task, key, value)

        if task.task_status.name not in ["执行中", "已执行", "已完成"]:
            if body.is_manage_task:
                setattr(task, "frame", None)
                case_ids = []
                task_milestones = TaskMilestone.query.filter_by(task_id=task_id).all()
                for task_milestone in task_milestones:
                    for case in task_milestone.cases:
                        case_ids.append(case.id)
                    cases = Case.query.filter(Case.id.in_(case_ids)).all()
                    _ = [
                        task_milestone.cases.remove(item)
                        for item in cases
                        if item in task_milestone.cases
                    ]
                    task_milestone.add_update()
                    _ = [
                        db.session.delete(item)
                        for item in task_milestone.manual_cases
                        if item.case_id in case_ids
                    ]
            if body.frame:
                task.frame = body.frame
            if any([body.milestones, body.milestone_id]) and any(
                [
                    task.parents.filter(Task.is_delete.is_(False)).all(),
                    task.children.filter(Task.is_delete.is_(False)).all(),
                ]
            ):
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg="Tasks have associated tasks, and milestones are not allowed to be modified.",
                )
            if (
                task.type != "VERSION"
                and body.milestone_id
                and (
                    (
                        task.milestones
                        and body.milestone_id != task.milestones[0].milestone_id
                    )
                    or not task.milestones
                )
            ):
                for milestone in task.milestones:
                    _ = [db.session.delete(item) for item in milestone.manual_cases]
                    db.session.commit()
                _ = [db.session.delete(item) for item in task.milestones]
                db.session.commit()
                task.milestones.append(
                    TaskMilestone(task_id=task_id, milestone_id=body.milestone_id)
                )
                temp = Milestone.query.get(body.milestone_id)
                task.start_time = temp.start_time
                task.deadline = temp.end_time if not task.deadline else task.deadline
            elif task.type == "VERSION" and body.milestones:
                milestones = body.milestones
                if task.milestones:
                    old_milestones = [item.milestone_id for item in task.milestones]
                    delete_list = list(set(old_milestones) - set(milestones))
                    for item in TaskMilestone.query.filter(
                        TaskMilestone.task_id == task_id,
                        TaskMilestone.milestone_id.in_(delete_list),
                    ).all():
                        _ = [db.session.delete(cases) for cases in item.manual_cases]
                        db.session.commit()
                    _ = [
                        db.session.delete(item)
                        for item in task.milestones
                        if item.milestone_id in delete_list
                    ]
                    db.session.commit()
                    start_time_list = []
                    for item in milestones:
                        _milestone = Milestone.query.get(item)
                        if _milestone:
                            start_time_list.append(_milestone.start_time)
                    start_time_list.sort()
                    task.start_time = start_time_list[0] if start_time_list else None
                    milestones = set(milestones) - set(old_milestones)
                _ = [
                    task.milestones.append(
                        TaskMilestone(task_id=task_id, milestone_id=item)
                    )
                    for item in milestones
                ]
                temp = Milestone.query.get(body.milestones[0])
                task.start_time = temp.start_time
                task.deadline = temp.end_time if not task.deadline else task.deadline
        elif body.milestone_id or body.milestones or body.frame:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )
        task.add_update()
        db.session.commit()

        if body.status_id or body.status_name:
            result = UpdateTaskStatusService(
                task, body.status_id, body.status_name
            ).operate()
            if result:
                return result

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get(task_id):
        """
        获取一个任务的详细信息
        @param task_id:
        @return:
        """
        is_delete = True if request.args.get("is_delete") == "true" else False
        task = Task.query.filter_by(id=task_id, is_delete=is_delete).first()
        if not task:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="task is not exists")

        return_data = TaskInfoSchema(**task.__dict__).dict()
        return_data["originator"] = UserBaseSchema(
            **User.query.get(task.creator_id).__dict__
        ).dict()
        return_data["executor"] = UserBaseSchema(
            **User.query.get(task.executor_id).__dict__
        ).dict()
        group = None
        if task.group_id:
            group = Group.query.filter_by(is_delete=False, id=task.group_id).first()

        return_data["executor_group"] = (
            GroupInfoSchema(**group.to_dict()).dict() if group else None
        )
        return_data["tags"] = [
            TagInfoSchema(**item.__dict__).dict() for item in task.tags
        ]

        if task.milestones:
            milestones = [item.milestone_id for item in task.milestones]
            milestones = Milestone.query.filter(Milestone.id.in_(milestones)).all()
            return_data["milestones"] = [item.to_json() for item in milestones]
            if task.type != "VERSION":
                milestone = None
                if task.milestones:
                    milestone = Milestone.query.get(task.milestones[0].milestone_id)
                return_data["milestone"] = milestone.to_json()
        
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_milestone_tasks(milestone_id, query):
        def page_func(task: Task):
            item_dict = TaskInfoSchema(**task.__dict__).dict()
            return item_dict

        _filter = [
            TaskMilestone.milestone_id == milestone_id,
            Task.is_delete.is_(False),
        ]
        if query.title:
            _filter.append(Task.title.like(f"%{query.title}%"))
        query_filter = (
            Task.query.join(TaskMilestone).filter(*_filter).order_by(Task.create_time)
        )
        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
            func=page_func
        )

    @staticmethod
    @collect_sql_error
    def get_recycle_bin(query: PageBaseSchema):
        """
        获取回收站中的任务列表
        @return:
        """
        query_filter = Task.query.filter_by(
            is_delete=True,
            org_id=redis_client.hget(RedisKey.user(g.user_id), "current_org_id"),
        ).order_by(Task.update_time.desc(), Task.id.asc())

        def page_func(item: Task):
            item_dict = TaskRecycleBinInfo(**item.__dict__).dict()
            item_dict["originator"] = UserBaseSchema(
                **User.query.get(item.creator_id).__dict__
            ).dict()
            return item_dict

        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
            func=page_func
        )

    @staticmethod
    @collect_sql_error
    def delete_task_list(body: DeleteTaskList):
        if body.task_ids:
            for task_id in body.task_ids:
                task = Task.query.filter_by(id=task_id, creator_id=g.user_id).first()
                if not task:
                    continue
                if task and task.task_status.name == "待办中":
                    setattr(task, "is_delete", True)
                    task.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskParticipant(object):
    @staticmethod
    @collect_sql_error
    def get(task_id, query_task=False):
        """
        获取任务的协助者信息/获取当前组织中的所有协助者
        @param task_id:
        @param query_task:
        @return:
        """
        if query_task:
            current_org = int(
                redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
            )
            participants = (
                TaskParticipant.query.join(Task)
                .filter(Task.org_id == current_org)
                .all()
            )
        else:
            participants = TaskParticipant.query.filter_by(task_id=task_id).all()
        return_data = []
        for item in participants:
            if item.type == EnumsTaskExecutorType.GROUP.value:
                group = Group.query.filter_by(
                    is_delete=False, id=item.participant_id
                ).first()
                if not group:
                    continue
                participant = GroupInfoSchema(**group.to_dict()).dict()
            else:
                participant = UserBaseSchema(
                    **User.query.get(item.participant_id).__dict__
                ).dict()
            participant["participant_id"] = item.participant_id
            participant["participant_type"] = item.type
            participant["id"] = item.id
            return_data.append(participant)

        if query_task:
            return_data = [dict(t) for t in {tuple(d.items()) for d in return_data}]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def update(task_id, body):
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_delete.is_(False),
            or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
        ).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
     
        executor_to_participant_type = task.executor_type
        executor_to_participant_id = task.executor_id
        if task.executor_type == EnumsTaskExecutorType.GROUP.value:
            relationship = ReUserGroup.query.filter_by(
                is_delete=False,
                org_id=task.org_id,
                user_id=task.executor_id,
                role_type=GroupRole.create_user.value,
            ).first()
            executor_to_participant_id = relationship.group_id

        for item in body.participants:
            if (
                int(executor_to_participant_id) == int(item.participant_id)
                and executor_to_participant_type == item.type
            ):
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg="%s %s has been executor." % (executor_to_participant_type, item.participant_id),
                )

        participants = TaskParticipant.query.filter_by(task_id=task_id).all()
        del_pc = [_pc for _pc in participants]
        add_pc = [_pc for _pc in body.participants]
        for pc in participants:
            for item in body.participants:
                if pc.participant_id == item.participant_id and pc.type == item.type:
                    add_pc.remove(item)
                    del_pc.remove(pc)

        pm = PermissionManager()
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "execute_task.yaml"), task_id
        )
        for apc in add_pc:
            if apc.type == EnumsTaskExecutorType.GROUP.value:
                relationship = ReUserGroup.query.filter_by(
                    is_delete=False,
                    org_id=task.org_id,
                    group_id=apc.participant_id,
                    role_type=GroupRole.create_user.value,
                ).first()
                if not relationship:
                    return jsonify(
                        error_code=RET.NO_DATA_ERR, error_msg="group is not exists"
                    )
                _data = {
                    "permission_type": "group",
                    "org_id": task.org_id,
                    "group_id": relationship.group_id,
                }
                pm.bind_scope_nouser(
                    scope_datas_allow=scope_data_allow,
                    scope_datas_deny=scope_data_deny,
                    _data=_data,
                )
            else:
                user = User.query.filter_by(user_id=apc.participant_id).first()
                if not user:
                    return jsonify(
                        error_code=RET.NO_DATA_ERR, error_msg="user is not exists"
                    )
                if int(task.creator_id) != int(apc.participant_id):
                    pm.bind_scope_user(
                        scope_datas_allow=scope_data_allow,
                        scope_datas_deny=scope_data_deny,
                        user_id=apc.participant_id,
                    )
            participant = TaskParticipant(
                task_id=task_id, participant_id=apc.participant_id, type=apc.type
            )
            db.session.add(participant)
            # add permission code
        for dpc in del_pc:
            # del permission code
            if dpc.type == EnumsTaskExecutorType.PERSON.value:
                if int(task.creator_id) == int(dpc.participant_id):
                    continue
                role = Role.query.filter_by(name=str(dpc.participant_id)).first()
            else:
                role = Role.query.filter_by(
                    name="admin", type="group", group_id=dpc.participant_id
                ).first()
            PermissionManager.unbind_scope_role(
                scope_data_allow,
                False,
                role.id,
            )
            db.session.delete(dpc)

        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskComment(object):
    @staticmethod
    @collect_sql_error
    def add(task_id, body):
        comment = TaskComment(
            task_id=task_id, content=body.content, creator_id=g.user_id
        )
        comment.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(task_id, query):
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_delete.is_(False),
            or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
        ).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if query.is_all:
            TaskComment.query.filter_by(task_id=task_id).delete(
                synchronize_session=False
            )
        elif query.comment_id:
            TaskComment.query.filter(
                TaskComment.id.in_(query.comment_id), TaskComment.task_id == task_id
            ).delete(synchronize_session=False)
        else:
            return jsonify(error_code=RET.PARMA_ERR, error_msg="request params error")
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get(task_id):
        """
        获取任务的评论信息
        @param task_id:
        @return:
        """
        comments = TaskComment.query.filter_by(task_id=task_id).all()
        return_data = []
        for item in comments:
            comment = UserBaseSchema(**User.query.get(item.creator_id).__dict__).dict()
            comment["content"] = item.content
            comment["id"] = item.id
            comment["create_time"] = item.create_time.strftime("%Y-%m-%d %H:%M:%S")
            return_data.append(comment)
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class HandlerTaskTag(object):
    @staticmethod
    @collect_sql_error
    def get():
        tags = TaskTag.query.all()
        return_data = [TagInfoSchema(**item.__dict__).dict() for item in tags]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def add(body: AddTaskTagSchema):
        task = Task.query.get(body.task_id)
        if not task or g.user_id not in [task.creator_id, task.executor_id]:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if body.id:
            tag = TaskTag.query.get(body.id)
            task.tags.append(tag)
            task.add_update()
            return jsonify(error_code=RET.OK, error_msg="OK")
        if not all([body.name, body.color]):
            return jsonify(error_code=RET.PARMA_ERR, error_msg="params is error")
        tag = TaskTag(name=body.name, color=body.color)
        task.tags.append(tag)
        task.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(query: DelTaskTagSchema):
        tag = TaskTag.query.get(query.id)
        if query.task_id:
            task = Task.query.get(query.task_id)
            if not task or g.user_id not in [task.creator_id, task.executor_id]:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="task is not exists / user is no right",
                )
            task.tags.remove(tag)
            task.add_update()
            return jsonify(error_code=RET.OK, error_msg="OK")
        tag.tasks.clear()
        db.session.delete(tag)
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskFamily(object):
    @staticmethod
    @collect_sql_error
    def add(task_id, body: AddFamilyMemberSchema):
        if not any([body.parent_id, body.child_id]):
            return jsonify(error_code=RET.PARMA_ERR, error_msg="params is error")
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_delete.is_(False),
            or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
        ).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if task.task_status.name in ["执行中", "已执行", "已完成"]:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )
        if body.parent_id:
            family_task = Task.query.filter(
                Task.id == body.parent_id, Task.is_delete.is_(False)
            ).first()
            if not family_task:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="task is not exists"
                )
            task.display = False
            task.parents.append(family_task)
        if body.child_id:
            family_task = Task.query.filter(
                Task.id == body.child_id, Task.is_delete.is_(False)
            ).first()
            if not family_task:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="task is not exists"
                )
            task.children.append(family_task)
            family_task.display = False
            family_task.add_update()
        task.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get(task_id, query: QueryFamilySchema):
        """
        获取任务的关联任务
        @param task_id:
        @param query:
        @return:
        """
        permission_filter = GetAllByPermission(Task).get_filter()
        if not task_id:
            _filter = [
                Task.is_delete.is_(False),
                Task.org_id
                == redis_client.hget(RedisKey.user(g.user_id), "current_org_id"),
            ]
            _filter.extend(permission_filter)
            tasks = Task.query.filter(*_filter).all()
            return_data = [TaskBaseSchema(**item.__dict__).dict() for item in tasks]
            return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

        if not query.not_in:
            task = Task.query.get(task_id)
            if not task:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="task is not exists / user is no right",
                )
            parents = [
                AnalysisTaskInfo(item).dict()
                for item in task.parents.filter(Task.is_delete.is_(False)).all()
            ]
            children = [
                AnalysisTaskInfo(item).dict()
                for item in task.children.filter(Task.is_delete.is_(False)).all()
            ]
            return_data = dict(parents=parents, children=children)
            return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

        task = Task.query.filter_by(id=task_id, is_delete=False).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if not task.milestones:
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="task need add milestone"
            )
        filter_params = [Task.is_delete.is_(False), Task.id != task_id]
        if query.title:
            filter_params.append(Task.title.like(f"%{query.title}%"))
        parents = set(
            [item.id for item in task.parents.filter(Task.is_delete.is_(False)).all()]
        )
        children = set(
            [item.id for item in task.children.filter(Task.is_delete.is_(False)).all()]
        )
        if not query.is_parent:
            family_member = get_family_member(
                parents, return_set=set(), is_parent=query.is_parent
            ).union(children)
        else:
            family_member = get_family_member(
                children, return_set=set(), is_parent=query.is_parent
            ).union(parents)
        filter_params.append(Task.id.notin_(family_member))
        filter_params.append(
            TaskMilestone.milestone_id.in_(
                [item.milestone_id for item in task.milestones]
            )
        )
        filter_params.extend(permission_filter)
        tasks = Task.query.join(TaskMilestone).filter(*filter_params).all()
        return_data = [TaskBaseSchema(**item.__dict__).dict() for item in tasks]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def delete(task_id: int, query: DelFamilyMemberSchema):
        if not any([query.parent_id, query.child_id]):
            return jsonify(error_code=RET.PARMA_ERR, error_msg="params is error")
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_delete.is_(False),
            or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
        ).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if task.task_status.name in ["执行中", "已执行", "已完成"]:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )
        if query.parent_id:
            family_task = Task.query.filter(
                Task.id.in_(query.parent_id), Task.is_delete.is_(False)
            ).all()
            if not family_task:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="task is not exists"
                )
            _ = [task.parents.remove(item) for item in family_task]
            task.add_update()
            _ = [update_task_display(item) for item in family_task]
        if query.child_id:
            family_task = Task.query.filter(
                Task.id.in_(query.child_id), Task.is_delete.is_(False)
            ).all()
            if not family_task:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="task is not exists"
                )
            _ = [task.children.remove(item) for item in family_task]
            task.add_update()
            _ = [update_task_display(item) for item in family_task]
        update_task_display(task)
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskReport(object):
    @staticmethod
    @collect_sql_error
    def update(task_id, body: TaskReportContentSchema):
        task = Task.query.filter(
            Task.id == task_id,
            Task.is_delete.is_(False),
            or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
        ).first()
        if not task:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task is not exists / user is no right",
            )
        if task.report:
            report = task.report
            report.title = body.title
            report.content = body.content
        else:
            report = TaskReportContent(
                task_id=task_id, content=body.content, title=body.title
            )

        report.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get(task_id):
        report = TaskReportContent.query.get(task_id)
        return_data = (
            dict(title=report.title, content=report.content) if report else None
        )
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class HandlerTaskCase(object):
    @staticmethod
    @collect_sql_error
    def get(task_id, query: QueryTaskCaseSchema):
        """
        获取任务的关联用例/获取所有的关联用例模糊查询title
        @param task_id:
        @param query:
        @return:
        """
        if not query.is_contain:
            task_milestone = TaskMilestone.query.filter_by(
                task_id=task_id, milestone_id=query.milestone_id
            ).first()
            if not task_milestone:
                return jsonify(error_code=RET.NO_DATA_ERR, error_msg="no find data")
            case_list = [item.id for item in task_milestone.cases]
            filter_params = [Case.deleted.is_(False), Case.id.notin_(case_list)]
            if query.case_name:
                filter_params.append(Case.name.like(f"%{query.case_name}%"))
            if query.suite_id:
                filter_params.append(Case.suite_id == query.suite_id)
            query_filter = Case.query.filter(*filter_params)
            return PageUtil.get_data(
                query_filter=query_filter,
                query=query,
            )
        task_milestones = TaskMilestone.query.filter_by(task_id=task_id).all()
        return_data = []
        for item in task_milestones:
            item_dict = item.to_json()
            item_dict["milestone"] = None
            if item.milestone_id:
                item_dict["milestone"] = Milestone.query.get(
                    item.milestone_id
                ).to_json()
            return_data.append(item_dict)
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def add(task_id, milestone_id, body: AddTaskCaseSchema):
        task_milestone = (
            TaskMilestone.query.join(Task)
            .filter(
                TaskMilestone.task_id == task_id,
                Task.is_delete.is_(False),
                TaskMilestone.milestone_id == milestone_id,
                or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
            )
            .first()
        )
        if not task_milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task or template is not exists / user is no right",
            )
        if task_milestone.task.task_status.name in ["执行中", "已执行", "已完成"]:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )

        cases = Case.query.filter(
            Case.id.in_(body.case_id), Case.deleted.is_(False)
        ).all()
        _ = [
            task_milestone.cases.append(item)
            for item in cases
            if item not in task_milestone.cases
        ]
        task_milestone.add_update()
        judge_task_automatic(task_milestone)
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(task_id, milestone_id, query: DelTaskCaseSchema):
        task_milestone = (
            TaskMilestone.query.join(Task)
            .filter(
                TaskMilestone.task_id == task_id,
                Task.is_delete.is_(False),
                TaskMilestone.milestone_id == milestone_id,
                or_(Task.creator_id == g.user_id, Task.executor_id == g.user_id),
            )
            .first()
        )
        if not task_milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="task or template is not exists / user is no right",
            )
        if task_milestone.task.task_status.name in ["执行中", "已执行", "已完成"]:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )

        cases = Case.query.filter(Case.id.in_(query.case_id)).all()
        _ = [
            task_milestone.cases.remove(item)
            for item in cases
            if item in task_milestone.cases
        ]
        task_milestone.add_update()
        _ = [
            db.session.delete(item)
            for item in task_milestone.manual_cases
            if item.case_id in query.case_id
        ]
        db.session.commit()
        judge_task_automatic(task_milestone)
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def task_cases_result(task_id):
        # 获取任务
        task = Task.query.filter_by(id=task_id, is_delete=False).first()
        if not task:
            return dict(error_code=RET.NO_DATA_ERR, error_msg="task is not exists")
        # 获取子任务
        # 所有的任务
        tasks = [task]
        # 里程碑 开始时间 结束时间 测试用例数 问题单数 用例执行结果
        job_list = []
        # 提取任务中的执行结果
        for item in tasks:
            for milestone in item.milestones:
                milestone = Milestone.query.get(milestone.id)
                if not milestone:
                    continue
                job = Job.query.get(milestone.job_id)
                if not job:
                    continue
                job_data = job.to_json()
                job_data["milestone"] = milestone.to_json()
                cases = []
                for case in milestone.cases:
                    case_data = case.to_json()
                    analysis = Analyzed.query.filter(
                        Analyzed.case_id == case.id, Analyzed.job_id == job.id
                    ).all()
                    case_data["analysis"] = [item.to_json() for item in analysis]
                    cases.append(case)
                job_data["cases"] = cases
                job_list.append(job_data)
        return jsonify(error_code=RET.OK, error_msg="OK", data=job_list)

    @staticmethod
    @collect_sql_error
    def distribute(task_id, milestone_id, body: DistributeTaskCaseSchema):
        task_milestone = TaskMilestone.query.filter_by(
            task_id=task_id, milestone_id=milestone_id
        ).first()
        if task_milestone.task.task_status.name == "已完成":
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="current task status not allowed operate",
            )
        if task_milestone.task.task_status.name == "执行中":
            manual_case_id = [item.case_id for item in task_milestone.manual_cases]
            if (
                set(body.cases) - set(manual_case_id)
                and task_milestone.job_result == "running"
            ):
                return jsonify(
                    error_code=RET.PARMA_ERR, error_msg="current cass running"
                )
        cases = Case.query.filter(Case.id.in_(body.cases)).all()
        _ = [
            task_milestone.cases.remove(item)
            for item in cases
            if item in task_milestone.cases
        ]
        task_milestone.add_update()
        _ = [
            db.session.delete(item)
            for item in task_milestone.manual_cases
            if item.case_id in body.cases
        ]
        db.session.commit()
        judge_task_automatic(task_milestone)
        child_task = Task.query.get(body.child_task_id)
        child_task_milestone = TaskMilestone.query.filter_by(
            task_id=body.child_task_id, milestone_id=milestone_id
        ).first()
        if child_task_milestone:
            _ = [
                child_task_milestone.cases.append(item)
                for item in cases
                if item not in child_task_milestone.cases
            ]
            child_task_milestone.add_update()
        elif not child_task.milestones and not child_task_milestone:
            child_task_milestone = TaskMilestone(
                task_id=body.child_task_id, milestone_id=milestone_id
            )
            child_task_milestone.cases = cases
            child_task_milestone.add_update()
        else:
            return jsonify(
                error_code=RET.PARMA_ERR, error_msg="child task not have milestone"
            )
        automatic = True
        for item in child_task_milestone.cases:
            if not item.usabled:
                if item.id in body.cases:
                    child_task_milestone.manual_cases.append(
                        TaskManualCase(
                            task_milestone_id=child_task_milestone.id, case_id=item.id
                        )
                    )
                automatic = False
                break
        child_task_milestone.add_update()
        child_task.automatic = automatic
        child_task.status_id = TaskStatus.query.filter_by(name="待办中").first().id
        child_task.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskMilestone(object):
    @staticmethod
    @collect_sql_error
    def update_task_process(taskmilestone_id: int, body: TaskJobResultSchema):
        task_milestone = TaskMilestone.query.get(taskmilestone_id)
        task = task_milestone.task
        automatic = True
        done, block = True, False
        for item in task.milestones:
            if automatic and item.manual_cases:
                automatic = False
            if item.id == taskmilestone_id:
                item.job_result = body.result
                item.add_update()
            if item.job_result == "block":
                done, block = False, True
            elif item.job_result != "done":
                done = False
        status = None
        msg = None
        if done and not block and automatic:
            status = TaskStatus.query.filter_by(name="已执行").first()
            msg = f"{task.title}中的自动测试用例执行结束，执行完成，请注意查看！"
        elif not done and block:
            status = TaskStatus.query.filter_by(name="进行中").first()
            msg = f"{task.title}中的自动测试用例执行结束，执行受阻，请注意查看！"
        if msg:
            send_message(task, msg=msg)
        task.status_id = status.id if status else task.status_id
        task.automatic = automatic
        task.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update_manual_cases_result(
        task_id, taskmilestone_id, case_id, body: TaskCaseResultSchema
    ):
        task_milestone = TaskMilestone.query.get(taskmilestone_id)
        task = task_milestone.task
        if not task or task_id != task.id:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="task is not exists")
        manual_case = TaskManualCase.query.filter_by(
            task_milestone_id=taskmilestone_id, case_id=case_id
        ).first()
        if not manual_case:
            manual_case = TaskManualCase(
                task_milestone_id=taskmilestone_id,
                case_id=case_id,
                case_result=body.result,
            )
            task_milestone.manual_cases.append(manual_case)
            task_milestone.add_update()
            return jsonify(error_code=RET.OK, error_msg="OK")
        manual_case.case_result = body.result
        manual_case.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskStatistics(object):
    @collect_sql_error
    def __init__(self, query: QueryTaskStatisticsSchema):
        self.query = query
        filter_params = [Task.is_delete.is_(False)]
        if query.start_time:
            filter_params.append(
                or_(Task.start_time >= query.start_time, Task.start_time.is_(None))
            )
        if query.end_time:
            filter_params.append(
                or_(Task.deadline <= query.end_time, Task.deadline.is_(None))
            )
        if query.type:
            filter_params.append(Task.type == query.type)
            if query.type == "PERSON":
                filter_params.append(Task.executor_id == g.user_id)
        if query.executors and query.type != "PERSON":
            filter_params.append(Task.executor_id.in_(query.executors))
        if query.groups:
            filter_params.append(Task.group_id.in_(query.groups))
        if query.milestone_id:
            filter_params.append(TaskMilestone.milestone_id == query.milestone_id)
            self.tasks = Task.query.join(TaskMilestone).filter(*filter_params).all()
        else:
            self.tasks = Task.query.filter(*filter_params).all()
        self.expired_tasks = []
        self.accomplish_tasks = []

    def analyze_number(self):
        total = len(self.tasks)
        accomplish = 0
        no_accomplish = total
        today_expire = 0
        expired = 0
        for task in self.tasks:
            if task.accomplish_time:
                self.accomplish_tasks.append(task)
                accomplish += 1
                no_accomplish -= 1
            if task.deadline and task.deadline.date() == datetime.now(tz=pytz.timezone('Asia/Shanghai')).date():
                today_expire += 1
            if task.deadline and (
                not task.accomplish_time or task.deadline <= task.accomplish_time
            ):
                self.expired_tasks.append(task)
                expired += 1
        return [total, accomplish, no_accomplish, today_expire, expired]

    @staticmethod
    @collect_sql_error
    def analyze_executor(tasks):
        executor_list = [
            (item.executor_type, item.executor_id, item.group_id) for item in tasks
        ]
        executor_set = set(executor_list)
        executor_data = {}
        for item in executor_set:
            item_count = executor_list.count(item)
            if item[0] == "PERSON":
                executor = User.query.get(item[1])
                executor_data[executor.user_name] = item_count
            elif item[0] == "GROUP":
                executor = ReUserGroup.query.filter_by(
                    user_id=item[1], group_id=item[2], is_delete=False
                ).first()
                if executor:
                    key = f"{executor.user.user_name}({executor.group.name})"
                    executor_data[key] = item_count
        return executor_data

    def analyze_expired(self):
        return self.analyze_executor(self.expired_tasks)

    def analyze_tasks(self):
        return self.analyze_executor(self.tasks)

    @staticmethod
    def analyze_date_step(start_time, end_time):
        days = abs((end_time - start_time).days)
        if days == 0:
            return [start_time], [start_time]
        date_list = [
            start_time + timedelta(days=i) for i in range(0, days, math.ceil(days / 30))
        ]
        if end_time not in date_list:
            date_list.append(end_time)
        day_axis = [f"{item.year}-{item.month}-{item.day}" for item in date_list]
        if days < 30:
            return day_axis, date_list
        month_axis = [f"{item.year}-{item.month}" for item in date_list]
        year_axis = [f"{item.year}" for item in date_list]

        def wrapper(axis: list):
            flag = True
            for item in set(axis):
                if axis.count(item) > 2:
                    flag = False
                    break
            return flag

        if wrapper(year_axis):
            return year_axis, date_list

        if wrapper(month_axis):
            return month_axis, date_list
        return day_axis, date_list

    def analyze_burn_up(self):
        start_time = self.query.start_time
        if not start_time:
            start_task = (
                Task.query.filter(
                    Task.start_time.isnot(None), Task.is_delete.is_(False)
                )
                .order_by(Task.start_time.asc())
                .first()
            )
            start_time = (
                parser.parser("1970-01-01") if not start_task else start_task.start_time
            )
        end_time = self.query.end_time if self.query.end_time else datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        x_axis, date_list = self.analyze_date_step(start_time.date(), end_time.date())

        total = len(self.tasks)
        accomplish_list = [
            item.accomplish_time.date() for item in self.accomplish_tasks
        ]
        accomplish_set = set(accomplish_list)
        accomplish_tuple = [
            (item, accomplish_list.count(item)) for item in accomplish_set
        ]
        if not accomplish_tuple:
            return x_axis, [total for _ in range(len(x_axis))]
        accomplish_tuple.sort(key=lambda x: x[0])
        y_axis = []
        for item in date_list:
            remove_list = []
            for accomplish_task in accomplish_tuple:
                if item >= accomplish_task[0]:
                    total = total - accomplish_task[1]
                    remove_list.append(accomplish_task)
                else:
                    break
            y_axis.append(total)
            _ = [accomplish_tuple.remove(temp) for temp in remove_list]
        return x_axis, y_axis

    def run(self):
        numbers = self.analyze_number()
        burn_down_time, burn_down_count = self.analyze_burn_up()
        task_overtime = self.analyze_expired()
        task_distribute = self.analyze_tasks()
        issues = [] if not self.query.milestone_id else self.get_issues_v8()
        return_data = {
            "total": numbers[0],
            "accomplish": numbers[1],
            "not_accomplish": numbers[2],
            "count_today": numbers[3],
            "overtime_count": numbers[4],
            "burn_down_time": burn_down_time,
            "burn_down_count": burn_down_count,
            "total_day": len(burn_down_time),
            "task_overtime": task_overtime,
            "task_distribute": task_distribute,
            "issues": issues,
        }
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    def get_issues_v8(self):
        milestone = Milestone.query.get(self.query.milestone_id)
        if not milestone or milestone.is_sync is False:
            return []

        org = Organization.query.filter_by(
            id=redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        ).first()
        if not org or not org.enterprise_id:
            return []

        params = self.query.__dict__
        params.update(
            {
                "state": "active",
                "sort": "created",
                "direction": "desc",
                "milestone_id": milestone.gitee_milestone_id,
            }
        )

        _resp = GiteeV8BaseIssueHandler().get_all(GiteeIssueQueryV8(**params).__dict__)

        if not isinstance(_resp, Response):
            return []
        try:
            resp = json.loads(_resp.text)
            if resp.get("error_code") != RET.OK:
                return []
            issue_list = resp.get("data")
            if not isinstance(issue_list, list):
                issue_list = json.loads(issue_list)
            return issue_list
        except (AttributeError, json.JSONDecodeError) as e:
            current_app.logger.error(
                f"query issue list {issue_list} failed because {str(e)}"
            )
            return []


class HandlerTaskExecute(object):
    def __init__(self):
        self.task = None

    @collect_sql_error
    def create(self, params: OutAddTaskSchema):
        status = TaskStatus.query.filter_by(name="进行中").first()
        executor = ReUserGroup.query.filter_by(
            group_id=params.group_id, role_type=1, is_delete=False
        ).first()
        milestone = Milestone.query.get(params.milestone_id)
        if not all([executor, status, milestone]):
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="group/task status no find"
            )
        if Task.query.filter_by(title=params.title, is_delete=False).first():
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="task has exist")
        g.user_id = executor.user_id
        record = Task()
        record.title = params.title
        record.group_id = params.group_id
        record.executor_type = "GROUP"
        record.executor_id = executor.user.user_id
        record.creator_id = executor.user.user_id
        record.type = "VERSION"
        record.permission_type = "org"
        record.org_id = executor.org_id
        record.frame = params.frame
        record.status_id = status.id
        record.start_time = milestone.start_time
        record.deadline = milestone.end_time
        task_id = record.add_flush_commit_id()
        _data = {
            "permission_type": record.permission_type,
            "org_id": record.org_id,
            "group_id": record.group_id,
        }
        pm = PermissionManager()
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "task.yaml"), task_id
        )
        pm.generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data,
        )
        self.task = Task.query.get(task_id)
        task_milestone = TaskMilestone()
        task_milestone.task_id = task_id
        task_milestone.milestone_id = params.milestone_id
        task_milestone.cases = Case.query.filter(
            Case.id.in_(params.cases), Case.deleted.is_(False)
        ).all()
        task_milestone_id = task_milestone.add_flush_commit_id()
        auto_cases, manual_cases = UpdateTaskStatusService.split_cases(
            task_milestone.cases
        )
        if not manual_cases:
            self.task.automatic = True
            self.task.add_update()
        else:
            db.session.execute(
                TaskManualCase.__table__.insert(),
                [
                    {
                        "task_milestone_id": task_milestone_id,
                        "case_id": item.id,
                        "task_id": task_id,
                    }
                    for item in manual_cases
                ],
            )
            db.session.commit()
        return self

    @collect_sql_error
    def execute(self):
        result = UpdateTaskStatusService(self.task, status_name="执行中").operate()
        if result:
            return result
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerCaseTask(object):
    @staticmethod
    @collect_sql_error
    def get_task_info(case_id):
        filter_param = [Case.id == case_id]
        task = Task.query.filter(*filter_param).first()
        return HandlerTask.get(task.id)


class HandlerCaseFrame(object):
    @staticmethod
    @collect_sql_error
    def get_task_frame():
        _frame = str(Frame)
        index = _frame.index("[", 0, len(_frame))
        frame = ast.literal_eval(_frame[index : len(_frame)])
        return jsonify(error_code=RET.OK, error_msg="OK", data=frame)


class HandlerTaskProgress(object):
    def __init__(self, milestone_id) -> None:
        self.milestone_id = milestone_id
        self.all_node_ids = list()
        self.all_task_case_node_infos = dict()
        self.task_ids = list()
        self.all_task_test_case_infos = dict()
        self.all_task_test_static_info = dict()
        self.task = None
        try:
            self.get_version_task()
        except RuntimeError as e:
            raise RuntimeError(str(e)) from e
        self.task_key = f"MILESTONE_{self.milestone_id}_TASK_{self.task.id}_TEST_INFO"
        _key = redis_client.keys(self.task_key)
        if not _key:
            self.get_task_case_node()
            HandlerTaskProgress.get_test_infos_by_task(
                self.task,
                self.all_task_case_node_infos,
                self.task_ids,
                self.all_task_test_case_infos,
                self.all_task_test_static_info
            )
            self.save_test_info_to_redis()
        else:
            self.get_test_info_from_redis()

    def save_test_info_to_redis(self):
        redis_client.hmset(
            self.task_key, 
            {
                "milestone_id": self.milestone_id,
                "task_id": self.task.id,
                "all_task_ids": self.task_ids,
                "all_node_ids": self.all_node_ids,
                "all_task_case_node_infos": json.dumps(self.all_task_case_node_infos),
                "all_task_test_case_infos": json.dumps(self.all_task_test_case_infos),
                "all_task_test_static_info": json.dumps(self.all_task_test_static_info),
            }
        )
        redis_client.expire(self.task_key, 60 * 30)

    def get_test_info_from_redis(self):
        task_id = redis_client.hget(
            self.task_key, "task_id")
        self.task = Task.query.get(task_id)
        all_task_ids = redis_client.hget(
            self.task_key, "all_task_ids")
        self.task_ids += list(map(int, all_task_ids[1:-1].split(",")))
        all_node_ids = redis_client.hget(
            self.task_key, "all_node_ids")
        self.all_node_ids += list(map(int, all_node_ids[1:-1].split(",")))
        all_task_case_node_infos = redis_client.hget(
            self.task_key, "all_task_case_node_infos")
        self.all_task_case_node_infos.update(json.loads(all_task_case_node_infos))
        all_task_test_case_infos = redis_client.hget(
            self.task_key, "all_task_test_case_infos")
        self.all_task_test_case_infos.update(json.loads(all_task_test_case_infos))
        all_task_test_static_info = redis_client.hget(
            self.task_key, "all_task_test_static_info")
        self.all_task_test_static_info.update(json.loads(all_task_test_static_info))

    def get_version_task(self):
        """
        :description: Get the version task associated with the milestone
        """
        #一个里程碑可以创建多个版本任务，这块没有做限制
        task = Task.query.join(TaskMilestone).filter(
            Task.id == TaskMilestone.task_id,
            TaskMilestone.milestone_id == self.milestone_id,
            Task.type == "VERSION",
            Task.is_delete.is_(False),
            Task.case_node_id.isnot(None),
        ).first()
        if not task:
            raise RuntimeError("no version task.")
        if task and not task.children:
            raise RuntimeError("task not assigned.")
        self.task = task

    @staticmethod
    def get_case_node(case_node, case_node_infos: dict, all_node_ids: list, source: str=""):
        """
        :description: Get all child case_nodes under the case_node
        :param: case_node_infos: dict, store all child case_node whose type is case under the case_node
        :param: all_node_ids: list, store all child case_node ids under the case_node
        :param: source: str, a temporary variable
        """
        if case_node.type == "case":
            tmp_source = source + "," + str(case_node.id)
            [all_node_ids.append(_id) for _id in  list(map(int, tmp_source[1:].split(","))) if _id not in all_node_ids]
            case_node_infos.update(
                {
                    str(case_node.case_id): {
                        "case_node_id": case_node.id,
                        "source": tmp_source[1:],
                    }
                }
            )
        else:
            tmp_source = source + "," + str(case_node.id)
            if not case_node.children.all():
                return
            for case_node_tmp in case_node.children.all():
                HandlerTaskProgress.get_case_node(case_node_tmp, case_node_infos, all_node_ids, tmp_source)

    @collect_sql_error
    def get_task_case_node(self):
        """
        :description: Get all child case_nodes under the version task
        :return: 
            case_node_infos: dict, store all child case_node whose type is case under the case_node
            all_node_ids: list, store all child case_node ids under the case_node
        """
        case_node = CaseNode.query.filter_by(id=self.task.case_node_id).first()
        HandlerTaskProgress.get_case_node(case_node, self.all_task_case_node_infos, self.all_node_ids)

    @staticmethod
    def get_test_infos_by_task(task, all_case_infos: dict, task_ids: list, task_case_infos: dict, test_stat_info: dict):
        """
        :description: Get task-related test infoinformation
        :param: all_case_infos: dict, all task-related case information
        :param: task_ids: list, store all child task ids under the task
        :param: task_case_infos: dict, store all task-related case test information
        :param: test_stat_info: dict, store task-related case test statistics information
        """
        if task.type != "VERSION":
            task_ids.append(task.id)
            tm = TaskMilestone.query.filter(
                TaskMilestone.task_id == task.id,
            ).first()
            query_filter = [
                Analyzed.job_id == tm.job_id,
            ]

            for auto_case in tm.cases:
                query_filter.append(Analyzed.case_id == auto_case.id)
                case_analyze = Analyzed.query.filter(*query_filter).first()
                task_case_infos.update({
                    str(auto_case.id): {
                        "result": case_analyze.result if case_analyze else "pending",
                        "task_id": task.id,
                        "type": "auto",
                    }
                })
                task_case_infos[str(auto_case.id)].update(all_case_infos.get(str(auto_case.id)))
                result = task_case_infos[str(auto_case.id)]["result"]
                if test_stat_info.get(result):
                    test_stat_info.update({result: test_stat_info.get(result) + 1})
                else:
                    test_stat_info.update({result: 1})

            for manual_case in tm.manual_cases:
                task_case_infos.update({
                    str(manual_case.case_id): {
                        "result": manual_case.case_result,
                        "task_id": task.id,
                        "type": "manual",
                    }
                })
                task_case_infos[str(manual_case.case_id)].update(all_case_infos.get(str(manual_case.case_id)))
                result = task_case_infos[str(manual_case.case_id)]["result"]
                if test_stat_info.get(result):
                    test_stat_info.update({result: test_stat_info.get(result) + 1})
                else:
                    test_stat_info.update({result: 1})

        for sub_task in task.children.filter(Task.is_delete.is_(False)).all():
            HandlerTaskProgress.get_test_infos_by_task(
                sub_task,
                all_case_infos,
                task_ids,
                task_case_infos,
                test_stat_info
            )

    def get_latest_test_infos(self):
        """
        获取版本任务最新统计测试进展
        """
        tm = TaskMilestone.query.filter(
            TaskMilestone.task_id == self.task.id,
        ).first()
        query_filter = [
            Analyzed.job_id == tm.job_id,
        ]
        test_stat_info = dict()
        for case_id in self.all_task_test_case_infos.keys():
            _type = self.all_task_test_case_infos.get(case_id).get("type")
            if _type == "auto":
                query_filter.append(Analyzed.case_id == int(case_id))
                case_analyze = Analyzed.query.filter(*query_filter).first()
                self.all_task_test_case_infos.get(case_id).update(
                    {"result": case_analyze.result if case_analyze else "pending"}
                )
            else:
                munual_case = TaskManualCase.query.filter_by(id=int(case_id)).first()
                self.all_task_test_case_infos.get(case_id).update(
                    {"result": munual_case.case_result if munual_case else "unknown"}
                )
            result = self.all_task_test_case_infos.get(case_id).get("result")
            if test_stat_info.get(result):
                test_stat_info.update({result: test_stat_info.get(result) + 1})
            else:
                test_stat_info.update({result: 1})
        self.all_task_test_static_info = test_stat_info
        self.save_test_info_to_redis()

    def get_task_test_progress(self):
        return self.get_task_case_node_and_test_progress(self.task.case_node_id, False)
    
    def get_milestone_test_progress(self):
        test_stat_info = HandlerTaskProgress.statistic(self.all_task_test_static_info)
        return test_stat_info.get("test_progress")

    def get_test_progress_by_case_node(self, case_node_id):
        """
        根据case_node_id统计测试进展
        """
        test_static_info = dict()
        for case_id in self.all_task_test_case_infos.keys():
            case_node_path = self.all_task_test_case_infos.get(case_id).get("source")
            if (
                case_node_path.startswith(str(case_node_id) + ",") 
            ) or (
                case_node_path.find("," + str(case_node_id) + ",") > -1
            ):
                result = self.all_task_test_case_infos.get(case_id).get("result")
                if test_static_info.get(result):
                    test_static_info.update({result: test_static_info.get(result) + 1})
                else:
                    test_static_info.update({result: 1})
        return HandlerTaskProgress.statistic(test_static_info)

    def get_test_progress_by_task(self, task_id):
        """
        根据task_id统计测试进展
        """
        if task_id not in self.task_ids:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="this task does not belong to the current milestone.",
            )
        test_static_info = dict()
        for case_id in self.all_task_test_case_infos.keys():
            tmp_task_id = self.all_task_test_case_infos.get(case_id).get("task_id")
            if int(task_id) == int(tmp_task_id):
                result = self.all_task_test_case_infos.get(case_id).get("result")
                if test_static_info.get(result):
                    test_static_info.update({result: test_static_info.get(result) + 1})
                else:
                    test_static_info.update({result: 1})

        return_data = HandlerTaskProgress.statistic(test_static_info)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data
        )

    @staticmethod
    def statistic(test_static_info):
        from server.utils.math_util import calculate_rate
        tmp_test_static_info = dict()
        tmp_test_static_info.update(test_static_info)

        all_cnt = 0
        for _result in test_static_info.keys():
            _count = test_static_info.get(_result)
            all_cnt += _count
        tmp_test_static_info.update(
            {
                "all_cnt": all_cnt
            }
        )
        test_progress_cnt = 0
        if test_static_info.get("failed"):
            test_progress_cnt += test_static_info.get("failed")
        if test_static_info.get("success"):
            test_progress_cnt += test_static_info.get("success")
        tmp_test_static_info.update(
            {
                "test_progress": calculate_rate(test_progress_cnt, all_cnt, 2)
            }
        )

        for _result in test_static_info.keys():
            _count = test_static_info.get(_result)
            tmp_test_static_info.update(
                {
                    _result+"_rate": calculate_rate(_count, all_cnt, 2)
                }
            )
        return tmp_test_static_info

    @collect_sql_error
    def get_task_case_node_and_test_progress(self, case_node_id, unfold:bool=True):
        from server.schema.testcase import CaseNodeBaseSchema
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="case_node does not exists"
            )
        if case_node_id not in self.all_node_ids:
            return jsonify(
                error_code=RET.DB_DATA_ERR,
                error_msg="case_node no right"
            )

        return_data = CaseNodeBaseSchema(**case_node.__dict__).dict()
        if unfold:
            return_data["children"] = list()
            children = CaseNode.query.filter(
                CaseNode.parent.contains(case_node)
            ).all()
            for child in children:
                if child.id in self.all_node_ids:
                    child_dict = child.to_json()
                    if child.type == 'case' and str(child.case_id) in self.all_task_test_case_infos.keys():
                        case_result = self.all_task_test_case_infos.get(str(child.case_id)).get("result")
                        child_dict["result"] = case_result
                    elif  child.type != 'case':
                        test_progress = self.get_test_progress_by_case_node(child.id)
                        if test_progress.get("all_cnt") == 0:
                            continue
                        child_dict["test_progress"] = test_progress
                    else:
                        continue
                    return_data["children"].append(child_dict)

        source = list()
        cur = case_node
        while cur:
            if not cur.parent.all():
                source.append(cur.id)
                break
            if len(cur.parent.all()) > 1:
                raise RuntimeError(
                    "case_node should not have parents beyond one")

            source.append(cur.id)
            cur = cur.parent[0]

        return_data["source"] = source
        if case_node.type == 'case':
            case_result = self.all_task_test_case_infos.get(str(case_node.case_id)).get("result")
            return_data["result"] = case_result
        else:
            test_progress = self.get_test_progress_by_case_node(case_node_id)
            return_data["test_progress"] = test_progress
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data
        )