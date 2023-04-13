# -*- coding: utf-8 -*-
# @Author : gaodi12
# @Email  : gaodi12@huawei.com
# @License: Mulan PSL v2
# @Date   : 2022-12-20 13:46:29
import time
import os
import pandas as pd
from flask import jsonify, g
from server import db, redis_client
from server.model.task import (
    TaskDistributeTemplate,
    DistributeTemplateType,
    Task,
    TaskStatus,
    TaskParticipant,
    TaskMilestone,
    TaskManualCase,
)
from server.model.testcase import Suite, Case
from server.model.group import ReUserGroup
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.redis_util import RedisKey
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import get_api
from .services import judge_task_automatic

base_dir = os.path.dirname(os.path.abspath(__file__))


class HandlerTemplate:
    @staticmethod
    @collect_sql_error
    def get(query):
        org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        rugs = ReUserGroup.query.filter_by(
            user_id=g.user_id,
            org_id=org_id,
            is_delete=False,
            user_add_group_flag=True,
        ).all()
        groups = [item.group_id for item in rugs]
        filter_params = [TaskDistributeTemplate.group_id.in_(groups)]
        if query.name:
            filter_params.append(TaskDistributeTemplate.name.like(f"%{query.name}%"))
        if query.group_id:
            filter_params.append(TaskDistributeTemplate.group_id == query.group_id)
        if query.type_name:
            filter_params.append(
                DistributeTemplateType.name.like(f"%{query.type_name}%")
            )
            query_filter = TaskDistributeTemplate.query.join(
                DistributeTemplateType
            ).filter(*filter_params)
        else:
            query_filter = TaskDistributeTemplate.query.filter(*filter_params)

        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
        )

    @staticmethod
    @collect_sql_error
    def add(body):
        org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        template = TaskDistributeTemplate(
            name=body.name,
            creator_id=g.user_id,
            group_id=body.group_id,
            permission_type="group",
            org_id=org_id,
        )
        if body.types:
            for item in body.types:
                dtt = DistributeTemplateType()
                dtt.name = item.name
                dtt.executor_id = item.executor_id
                dtt.creator_id = g.user_id
                dtt.group_id = template.group_id
                dtt.permission_type = template.permission_type
                dtt.suites = ",".join(item.suites)
                dtt.helpers = ",".join(item.helpers) if item.helpers else ""
                template.types.append(dtt)
        template.add_update()
        _data = {
            "permission_type": template.permission_type,
            "group_id": template.group_id,
        }
        scope_data_allow, scope_data_deny = get_api(
            "task", "template.yaml", "template", template.id
        )
        PermissionManager().generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data,
        )
        for _type in template.types:
            scope_data_allow, scope_data_deny = get_api(
                "task", "type.yaml", "type", _type.id
            )
            PermissionManager().generate(
                scope_datas_allow=scope_data_allow,
                scope_datas_deny=scope_data_deny,
                _data=_data,
            )
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(template_id, body):
        template = TaskDistributeTemplate.query.get(template_id)
        for key, value in body.dict().items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
        template.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(template_id):
        template = TaskDistributeTemplate.query.get(template_id)
        pm = PermissionManager()
        for item in template.types:
            pm.clean("/api/v1/tasks/distribute-templates/types/", [item.id])
            db.session.delete(item)
        db.session.commit()
        pm.clean("/api/v1/tasks/distribute-templates/", [template_id])
        db.session.delete(template)
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTemplateType:
    @staticmethod
    def get_all_suites(template: TaskDistributeTemplate):
        template_suites = []
        for item in template.types:
            if item.suites:
                template_suites = template_suites + item.suites.split(",")
        return template_suites

    @staticmethod
    @collect_sql_error
    def get(query):
        filter_params = [Suite.deleted.is_(False)]
        if query.type_id:
            return HandlerTemplateType.get_info(query.type_id)
        if query.template_id:
            template = TaskDistributeTemplate.query.get(query.template_id)
            template_suites = HandlerTemplateType.get_all_suites(template)
            filter_params.append(Suite.id.notin_(template_suites))
        query_filter = Suite.query.filter(*filter_params)

        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
        )

    @staticmethod
    @collect_sql_error
    def get_info(type_id):
        return_data = DistributeTemplateType.query.get(type_id)
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data.to_json())

    @staticmethod
    @collect_sql_error
    def add(template_id, body):
        template = TaskDistributeTemplate.query.get(template_id)
        if body.name in [item.name for item in template.types]:
            return jsonify(error_code=RET.PARMA_ERR, error_msg="name has exists")
        dtt = DistributeTemplateType()
        dtt.name = body.name
        dtt.creator_id = g.user_id
        dtt.executor_id = body.executor_id
        dtt.group_id = template.group_id
        dtt.permission_type = template.permission_type
        dtt.suites = ",".join(body.suites)
        dtt.helpers = ",".join(body.helpers)
        dtt_id = dtt.add_flush_commit_id()
        template.types.append(dtt)
        template.add_update()
        _data = {
            "permission_type": template.permission_type,
            "group_id": template.group_id,
        }
        scope_data_allow, scope_data_deny = get_api("task", "type.yaml", "type", dtt_id)
        PermissionManager().generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data,
        )
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(type_id, body):
        dtt = DistributeTemplateType.query.get(type_id)
        for key, value in body.dict().items():
            if hasattr(dtt, key) and value is not None:
                setattr(dtt, key, value)
        dtt.add_update()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(type_id):
        dtt = DistributeTemplateType.query.get(type_id)
        db.session.delete(dtt)
        db.session.commit()
        PermissionManager().clean(
            "/api/v1/tasks/distribute-templates/types/", [type_id]
        )
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskDistributeCass:
    def __init__(self):
        self.status = TaskStatus.query.filter_by(name="待办中").first()
        self.parent_task = None
        self.task_milestone = None

    @collect_sql_error
    def distribute(self, task_id, template_id, body):
        # 分析数据
        # milestone_id, case_id, suite_id
        task = Task.query.get(task_id)
        if not task or not task.group_id or task.type == "PERSON":
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task can not use template distribute cases",
            )
        self.parent_task = task
        _origin = [_ for _ in self.parent_task.children]
        task_milestone = TaskMilestone.query.filter_by(
            task_id=task_id, milestone_id=body.milestone_id
        ).first()
        if not task_milestone:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task milestone relationship no find",
            )
        self.task_milestone = task_milestone
        task_cases = task_milestone.distribute_df_data(body.distribute_all_cases)
        task_cases_df = pd.DataFrame(
            task_cases, columns=["milestone_id", "case_id", "suite_id", "case_result"]
        )
        # suite_id, executor_id, helpers, type_name
        template = TaskDistributeTemplate.query.get(template_id)
        if template.group_id != task.group_id:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task group not match template group",
            )
        template_cases = []
        template_types = []
        for item in template.types:
            template_types.append(item.name)
            if not item.suites:
                continue
            for suite in item.suites.split(","):
                template_cases.append(
                    (int(suite), item.executor_id, item.helpers, item.name)
                )
        template_cases_df = pd.DataFrame(
            template_cases, columns=["suite_id", "executor_id", "helpers", "type_name"]
        )
        merge_df = pd.merge(
            task_cases_df, template_cases_df, on="suite_id"
        ).reset_index(drop=True)
        merge_case_type = []
        if not merge_df.empty:
            merge_case_type = merge_df["type_name"].drop_duplicates().tolist()
            for item in merge_df["type_name"].drop_duplicates().tolist():
                temp_df = merge_df[merge_df.type_name == item]
                temp_df = temp_df.reset_index(drop=True)
                self.create_child_task(temp_df, template.group_id, body.milestone_id)
        null_case_type = list(set(template_types) - set(merge_case_type))
        for item in template.types:
            if item.name in null_case_type:
                self.create_no_case_task(item, template.group_id, body.milestone_id)
        _after = [_ for _ in self.parent_task.children]
        pm = PermissionManager()
        for _task in list(set(_after) - set(_origin)):
            _data = {
                "permission_type": _task.permission_type,
                "org_id": _task.org_id,
                "group_id": _task.group_id,
            }
            scope_data_allow, scope_data_deny = pm.get_api_list(
                "task", os.path.join(base_dir, "task.yaml"), _task.id
            )

            pm.generate(
                scope_datas_allow=scope_data_allow,
                scope_datas_deny=scope_data_deny,
                _data=_data,
            )
        return jsonify(error_code=RET.OK, error_msg="OK")

    def child_task(self, title, group_id, executor_id):
        child_task = Task()
        child_task.title = title
        child_task.type = "GROUP"
        child_task.permission_type = "group"
        child_task.group_id = group_id
        child_task.creator_id = g.user_id
        child_task.start_time = self.parent_task.start_time
        child_task.executor_id = executor_id
        child_task.deadline = self.parent_task.deadline
        child_task.org_id = self.parent_task.org_id
        child_task.frame = self.parent_task.frame
        child_task.status_id = self.status.id
        child_task_id = child_task.add_flush_commit_id()
        child_task = Task.query.get(child_task_id)
        return child_task

    @staticmethod
    def bind_scope(task_id, user_ids: list):
        pm = PermissionManager()
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "execute_task.yaml"), task_id
        )
        for user_id in user_ids:
            pm.bind_scope_user(
                scope_datas_allow=scope_data_allow,
                scope_datas_deny=scope_data_deny,
                user_id=user_id,
            )

    @staticmethod
    def add_helpers(task, helpers):
        if helpers:
            for item in helpers.split(","):
                tp = TaskParticipant()
                tp.task_id = task.id
                tp.participant_id = item
                task.participants.append(tp)
            task.add_update()

    @staticmethod
    def add_milestone(task, milestone_id, cases=None):
        task.automatic = False
        tm = TaskMilestone()
        tm.task_id = task.id
        tm.milestone_id = milestone_id
        if cases:
            task.automatic = True
            tm.cases = Case.query.filter(
                Case.id.in_(cases), Case.deleted.is_(False)
            ).all()
            for case in tm.cases:
                if not case.usabled:
                    tmc = TaskManualCase(case_id=case.id)
                    task.automatic = False
                    tm.manual_cases.append(tmc)
        tm.add_update()
        task.add_update()

    def create_no_case_task(self, item: DistributeTemplateType, group_id, milestone_id):
        title = (
            f"T{self.parent_task.id}_TM{item.name}"
            f'_M{milestone_id}_S{time.strftime("%Y%m%d%H%M%S")}'
        )
        child_task = self.child_task(title, group_id, item.executor_id)
        self.add_helpers(child_task, item.helpers)
        test_user_ids = [_i for _i in item.helpers.split(",")]
        test_user_ids.append(item.executor_id)
        self.bind_scope(child_task.id, test_user_ids)
        self.add_milestone(child_task, milestone_id)
        self.parent_task.children.append(child_task)
        self.parent_task.add_update()

    def create_child_task(self, df: pd.DataFrame, group_id, milestone_id):
        # milestone_id, case_id, suite_id, executor_id, helpers, type_name
        title = (
            f'T{self.parent_task.id}_TM{df.loc[0, "type_name"]}'
            f'_M{milestone_id}_S{time.strftime("%Y%m%d%H%M%S")}'
        )
        child_task = self.child_task(title, group_id, df.loc[0, "executor_id"])
        self.add_helpers(child_task, df.loc[0, "helpers"])
        test_user_ids = [_i for _i in df.loc[0, "helpers"].split(",")]
        test_user_ids.append(df.loc[0, "executor_id"])
        self.bind_scope(child_task.id, test_user_ids)
        self.add_milestone(
            child_task,
            milestone_id,
            df[df.milestone_id == milestone_id]["case_id"].tolist(),
        )
        self.parent_task.children.append(child_task)
        self.parent_task.add_update()
        # 父任务删除测试用例
        self.delete_task_cases(self.task_milestone, df["case_id"].tolist())

    @staticmethod
    def delete_task_cases(task_milestone: TaskMilestone, cases: list):
        tm_cases = task_milestone.cases.copy() if task_milestone.cases else []
        _ = [task_milestone.cases.remove(item) for item in tm_cases if item.id in cases]
        task_milestone.add_update()
        tm_manual_cases = (
            task_milestone.manual_cases.copy() if task_milestone.manual_cases else []
        )
        _ = [
            db.session.delete(item) for item in tm_manual_cases if item.case_id in cases
        ]
        db.session.commit()
        judge_task_automatic(task_milestone)
