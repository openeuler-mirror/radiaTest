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

import datetime
import json
from uuid import uuid1
from flask import g, current_app, url_for, jsonify
from typing import List
from server.utils.response_util import ssl_cert_verify_error_collect
from server import redis_client, db
from server.model.template import Template
from server.model.task import Task, TaskStatus, TaskManualCase, TaskMilestone
from server.model.testcase import Case
from server.model.group import Group, ReUserGroup
from server.model.user import User
from server.model.message import Message, MsgLevel
from server.utils.db import Insert
from server.utils.redis_util import RedisKey
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server.schema.user import UserBaseSchema
from server.schema.group import GroupInfoSchema
from server.schema.task import TaskInfoSchema
from server.utils.resource_utils import ResourceManager


class UpdateTaskStatusService(object):
    def __init__(self, task: Task, status_id: int = 0, status_name: str = None) -> None:
        self.task = task
        if status_id:
            self.status = TaskStatus.query.get(status_id)
        elif status_name:
            self.status = TaskStatus.query.filter_by(name=status_name).first()
        else:
            self.status = None

    def operate(self):
        if not self.status:
            return None
        if self.status.name != "待办中" and not self.task.milestones:
            return jsonify(
                error_code=RET.SERVER_ERR, error_msg="task mast need milestone"
            )
        if self.status.name == "执行中":
            return self.execute()
        elif self.status.name == "已执行":
            return self.executed()
        elif self.status.name == "已完成":
            return self.accomplish()
        else:
            return self.update_task_status()

    def update_task_status(self):
        self.task.status_id = self.status.id
        self.task.add_update()
        return None

    def accomplish(self):
        children = get_task_children(tasks=[self.task], children=[])
        accomplish_flag = True
        for child in children:
            if child.task_status.name != "已完成":
                accomplish_flag = False
                break
        if accomplish_flag:
            parents = self.task.parents.filter(Task.is_delete.is_(False)).all()
            for item in parents:
                send_message(item, msg=f"子任务{self.task.title}已完成。", from_id=g.user_id)
                if item.automatic_finish:
                    children_ = get_task_children(tasks=[item], children=[])
                    all_accomplish = True
                    for child in children_:
                        if child.id == self.task.id:
                            continue
                        if child.task_status.name != "已完成":
                            all_accomplish = False
                            break
                    if all_accomplish:
                        item.accomplish_time = datetime.datetime.now()
                        item.status_id = self.status.id

            self.task.accomplish_time = datetime.datetime.now()
            self.update_task_status()
        else:
            return jsonify(
                error_code=RET.SERVER_ERR, error_msg="task have child not accomplish"
            )

    @staticmethod
    def split_cases(cases: List[Case]):
        auto_cases, manual_cases = [], []
        for case in cases:
            if case.deleted:
                continue
            if case.usabled:
                auto_cases.append(case)
            else:
                manual_cases.append(case)
        return auto_cases, manual_cases

    @staticmethod
    def _create_manual_cases(new_cases: List[Case], milestone: TaskMilestone):
        old_cases = milestone.manual_cases
        if not old_cases:
            _ = [
                db.session.add(
                    TaskManualCase(task_milestone_id=milestone.id, case_id=item.id)
                )
                for item in new_cases
            ]
            db.session.commit()
        else:
            old_cases = set([item.case_id for item in milestone.manual_cases])
            new_cases = set([item.id for item in new_cases])
            _ = [
                db.session.delete(item)
                for item in milestone.manual_cases
                if item in list(old_cases - new_cases)
            ]
            db.session.commit()
            _ = [
                db.session.add(
                    TaskManualCase(task_milestone_id=milestone.id, case_id=item)
                )
                for item in list(new_cases - old_cases)
            ]
            db.session.commit()

    @ssl_cert_verify_error_collect
    def execute(self):
        result = None
        for task in [self.task]:
            status_id = task.status_id
            for milestone in task.milestones:
                auto_cases, manual_cases = UpdateTaskStatusService.split_cases(
                    milestone.cases
                )
                self._create_manual_cases(manual_cases, milestone)
                if not auto_cases:
                    task.status_id = self.status.id
                    continue
                template_id = milestone.template_id
                template_name = f"{task.title}_{uuid1().hex}"
                old_cases = None
                if template_id:
                    template = Template.query.get(template_id)
                    template_name = template.name
                    old_cases = template.cases
                    old_cases.sort(key=lambda x: x.id)
                    auto_cases.sort(key=lambda x: x.id)
                if not template_id or old_cases != auto_cases:
                    template = Template()
                    template.name = template_name
                    template.creator_id = g.user_id
                    template.org_id = int(
                        redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
                    )
                    template.milestone_id = milestone.milestone_id
                    template.permission_type = "person"
                    template.cases = auto_cases
                    template_id = template.add_flush_commit_id()
                    ResourceManager("template").add_permission(
                        "api_infos.yaml",
                        {
                            "creator_id": template.creator_id,
                            "org_id": template.org_id,
                            "permission_type": template.permission_type,
                        },
                        template_id,
                    )
                    milestone.template_id = template_id
                    milestone.job_result = "pending"
                    milestone.add_update()

                if (
                        milestone.job_result in ["pending", "block"]
                        and task.frame
                        and not task.is_manage_task
                ):
                    get_job_url = (
                        f'https://{current_app.config.get("SERVER_ADDR")}'
                        f'{url_for("run_template_event")}'
                    )

                    headers = {"content-type": "application/json"}

                    body = {
                        "id": template_id,
                        "taskmilestone_id": milestone.id,
                        "frame": task.frame,
                        "name": f"{template_name[:-15]}_{uuid1().hex}",
                    }
                    body_json = json.dumps(body)
                    verify = current_app.config.get("CA_CERT")
                    if current_app.config.get("CA_VERIFY") == "True":
                        verify = True
                    r = do_request(
                        "post",
                        get_job_url,
                        body=body_json,
                        headers=headers,
                        timeout=0.5,
                        verify=verify,
                    )

                    if r != 0 and r != 4:
                        current_app.logger.error("trigger job failed")
                        milestone.job_result = "pending"
                        task.status_id = status_id
                        result = jsonify(
                            error_code=RET.SERVER_ERR, error_msg="task trigger error"
                        )
                        break
                    else:
                        milestone.job_result = "running"
                        task.status_id = self.status.id
                else:
                    task.status_id = self.status.id
                db.session.add(milestone)
            if result:
                break
            db.session.add(task)
        if result:
            return result
        db.session.commit()

    def executed(self):
        job_done = True
        for item in self.task.milestones:
            if item.to_json().get("auto_cases", []) and item.job_result != "done":
                job_done = False
                break
            manual_cases_result = [
                case.case_result in ["success", "failed"] for case in item.manual_cases
            ]
            if not all(manual_cases_result):
                job_done = False
                break
        if not self.task.automatic and job_done:
            self.update_task_status()
        else:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="task is automatic task / task have case not accomplish",
            )


def get_task_children(tasks: list, children: list) -> list:
    task_children = []
    for task in tasks:
        task_children = [
            item
            for item in task.children
            if item not in children and not item.is_delete
        ]
    children = children + task_children
    if not task_children:
        return children
    child_tasks = Task.query.filter(
        Task.id.in_([item.id for item in task_children]), Task.is_delete.is_(False)
    ).all()
    return get_task_children(child_tasks, children)


def get_family_member(member_id: set, return_set: set, is_parent=True) -> set:
    return_set = return_set.union(member_id)
    if not member_id:
        return return_set
    tasks = Task.query.filter(Task.id.in_(member_id), Task.is_delete.is_(False)).all()
    for task in tasks:
        if not is_parent:
            members = task.parents.filter(Task.is_delete.is_(False)).all()
        else:
            members = task.children.filter(Task.is_delete.is_(False)).all()
        member_id = [item.id for item in members]
        member_id = set(member_id)
        return get_family_member(member_id, return_set, is_parent)


def update_task_display(task: Task):
    if not task.parents.filter(Task.is_delete.is_(False)).all():
        task.display = True
        task.add_update()


class AnalysisTaskInfo(object):
    def __init__(self, task: Task):
        self.task = task
        self.executor = None

    def get_executor(self):
        if self.executor is None:
            user = User.query.get(self.task.executor_id)
            self.executor = UserBaseSchema(**user.__dict__).dict() if user else {}
        return self.executor

    def get_belong(self):
        task = self.task
        if (
                (task.type in ["VERSION", "ORGANIZATION"] and task.executor_type == "GROUP")
                or task.type == "GROUP"
        ) and task.group_id:
            group = Group.query.get(task.group_id)
            return GroupInfoSchema(**group.to_dict()).dict() if group else {}
        else:
            return self.get_executor()

    def get_status(self):
        status = self.task.task_status
        return status.to_dict() if status else {}

    def dict(self):
        task_dict = TaskInfoSchema(**self.task.__dict__).dict()
        task_dict["status"] = self.get_status()
        task_dict["executor"] = self.get_executor()
        task_dict["belong"] = self.get_belong()
        return task_dict


def send_message(task: Task, msg, from_id=1):
    to_id = []
    for item in task.participants:
        if item.type == "PERSON":
            to_id.append(item.participant_id)
        else:
            re = ReUserGroup.query.filter_by(
                group_id=item.participant_id, role_type=1, is_delete=False
            ).first()
            if re:
                to_id.append(re.user_id)
    to_id.append(task.executor_id)
    to_id.append(task.creator_id)
    to_id = set(to_id)
    for item in to_id:
        Insert(
            Message,
            {
                "data": json.dumps({"info": msg}),
                "from_id": from_id,
                "to_id": item,
                "level": MsgLevel.system.value,
                "org_id": task.org_id
            },
        ).insert_id()


def judge_task_automatic(task_milestone: TaskMilestone):
    automatic = True
    if not task_milestone.cases:
        automatic = False
    else:
        for item in task_milestone.cases:
            if not item.usabled:
                automatic = False
                break
    task_milestone.task.automatic = automatic
    task_milestone.task.add_update()
