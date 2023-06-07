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
# @Date    : 2023/05/29
# @License : Mulan PSL v2
#####################################

import time
import json
from datetime import datetime
import pytz
import os
import pandas as pd
from server import db
from server.model.task import (
    TaskDistributeTemplate,
    Task,
    TaskStatus,
    TaskParticipant,
    TaskMilestone,
    TaskManualCase,
)
from server import redis_client, db
from server.model.testcase import Case, CaseNode
from server.utils.db import collect_sql_error
from server.utils.permission_utils import PermissionManager
from server.apps.task.services import judge_task_automatic
from celeryservice.lib import TaskHandlerBase


class TaskdistributeHandler(TaskHandlerBase):
    def __init__(self, logger):
        self.status = TaskStatus.query.filter_by(name="待办中").first()
        self.parent_task = None
        self.task_milestone = None
        super().__init__(logger)

    @collect_sql_error
    def distribute(self, task_id, template_id, body):
        # 分析数据
        task = Task.query.get(task_id)
        if not task or not task.group_id or task.type == "PERSON":
            return
        self.parent_task = task

        task_milestone = TaskMilestone.query.filter_by(
            task_id=task_id, milestone_id=body.get("milestone_id")
        ).first()
        if not task_milestone:
            return
        self.task_milestone = task_milestone
        task_cases = task_milestone.distribute_df_data(body.get("distribute_all_cases"))
        if len(task_cases) == 0:
            return
        task_cases_df = pd.DataFrame(
            task_cases, columns=["milestone_id", "case_id", "suite_id", "case_result"]
        )

        template = TaskDistributeTemplate.query.get(template_id)
        if template.group_id != task.group_id:
            return
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
        if len(template_cases) == 0:
            return
        task_key = f"DISTRIBUTE_TEMPLATE_{template_id}_TASK_{task_id}"
        redis_client.hmset(
            task_key,
            {
                "user_id": body.get("creator_id"),
                "resolve_time": datetime.now(
                    tz=pytz.timezone('Asia/Shanghai')
                ).strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        redis_client.expire(task_key, 1800)
        template_cases_df = pd.DataFrame(
            template_cases, columns=["suite_id", "executor_id", "helpers", "type_name"]
        )
        merge_df = pd.merge(
            task_cases_df, template_cases_df, on="suite_id"
        ).reset_index(drop=True)
        if not merge_df.empty:
            _origin = [_ for _ in self.parent_task.children]
            for item in merge_df["type_name"].drop_duplicates().tolist():
                temp_df = merge_df[merge_df.type_name == item]
                temp_df = temp_df.reset_index(drop=True)
                self.create_child_task(temp_df, template.group_id, body)

            _after = [_ for _ in self.parent_task.children]
            pm = PermissionManager(creator_id=body.get("creator_id"), org_id=task.org_id)
            for _task in list(set(_after) - set(_origin)):
                _data = {
                    "permission_type": _task.permission_type,
                    "org_id": _task.org_id,
                    "group_id": _task.group_id,
                }
                scope_data_allow, scope_data_deny = pm.get_api_list(
                    "task", os.path.join(body.get("base_dir"), "task.yaml"), _task.id
                )

                pm.generate(
                    scope_datas_allow=scope_data_allow,
                    scope_datas_deny=scope_data_deny,
                    _data=_data,
                )
        redis_client.delete(task_key)

    def child_task(self, title, group_id, executor_id, creator_id):
        child_task = Task()
        child_task.title = title
        child_task.type = "GROUP"
        child_task.permission_type = "group"
        child_task.group_id = group_id
        child_task.creator_id = creator_id
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
    def bind_scope(task_id, user_ids: list, base_dir):
        task = Task.query.get(task_id)
        pm = PermissionManager(creator_id=task.creator_id, org_id=task.org_id)
        scope_data_allow, scope_data_deny = pm.get_api_list(
            "task", os.path.join(base_dir, "execute_task.yaml"), task_id
        )
        for user_id in user_ids:
            pm.bind_scope_user(
                scope_datas_allow=scope_data_allow,
                scope_datas_deny=scope_data_deny,
                gitee_id=user_id,
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

    def create_child_task(self, df: pd.DataFrame, group_id, body):
        milestone_id = body.get("milestone_id")
        base_dir = body.get("base_dir")
        title = (
            f'T{self.parent_task.id}_TM{df.loc[0, "type_name"]}'
            f'_M{milestone_id}_S{time.strftime("%Y%m%d%H%M%S")}'
        )
        child_task = self.child_task(title, group_id, df.loc[0, "executor_id"], body.get("creator_id"))
        self.add_helpers(child_task, df.loc[0, "helpers"])
        test_user_ids = [_i for _i in df.loc[0, "helpers"].split(",")]
        test_user_ids.append(df.loc[0, "executor_id"])
        self.bind_scope(child_task.id, test_user_ids, base_dir)
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


class VersionTaskProgressHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def update_version_task_progress(self, task_id):
        task = Task.query.get(task_id)
        if task:
            self.logger.info(f"start statistics task {task.title} test progress")
            HandlerUpdateTaskProgress(task=task).update_task_progress()
            self.logger.info(f"end statistics task {task.title} test progress")


class AllVersionTaskProgressHandler(TaskHandlerBase):
    def update_all_version_task_progress(self):
        tasks = Task.query.filter(
            Task.type == "VERSION",
            Task.is_delete.is_(False),
            Task.case_node_id.isnot(None),
            Task.percentage != 100,
        ).all()
        for task in tasks:
            self.logger.info(f"start statistics task {task.title} test progress")
            HandlerUpdateTaskProgress(task=task).update_task_progress()
            self.logger.info(f"end statistics task {task.title} test progress")


class HandlerUpdateTaskProgress(object):
    def __init__(self, task) -> None:
        self.milestone_id = task.milestones[0].milestone_id
        self.all_node_ids = list()
        self.all_task_case_node_infos = dict()
        self.task_ids = list()
        self.all_task_test_static_info = dict()
        self.task = task
        self.task_key = f"MILESTONE_{self.milestone_id}_TASK_{self.task.id}_TEST_INFO"

    def update_task_progress(self):
        task_key = f"UPDATE_MILESTONE_{self.milestone_id}_TASK_{self.task.id}_TEST_PROGRESS"
        _key = redis_client.keys(task_key)
        if _key:
            return
        redis_client.hmset(
            task_key,
            {
                "resolve_time": datetime.now(
                    tz=pytz.timezone('Asia/Shanghai')
                ).strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        redis_client.expire(task_key, 1800)
        HandlerUpdateTaskProgress.get_all_tasks(self.task, self.task_ids)
        self.get_task_case_node()
        self.save_test_info_to_redis()
        redis_client.delete(task_key)

    def save_test_info_to_redis(self):
        redis_client.hmset(
            self.task_key, 
            {
                "milestone_id": self.milestone_id,
                "task_id": self.task.id,
                "all_task_ids": self.task_ids,
                "all_node_ids": self.all_node_ids,
                "all_task_case_node_infos": json.dumps(self.all_task_case_node_infos),
                "all_task_test_static_info": json.dumps(self.all_task_test_static_info),
            }
        )

    @staticmethod
    def get_case_node(case_node, case_node_infos: dict, all_node_ids: list, test_stat_info: dict, source: str=""):
        """
        :description: Get all child case_nodes under the case_node
        :param: case_node_infos: dict, store all child case_node whose type is case under the case_node
        :param: all_node_ids: list, store all child case_node ids under the case_node
        :param: source: str, a temporary variable
        """
        if case_node.type == "case":
            tmp_source = source + "," + str(case_node.id)
            [all_node_ids.append(_id) for _id in  list(map(int, tmp_source[1:].split(","))) if _id not in all_node_ids]
            result = case_node.case_result
            case_node_infos.update(
                {
                    str(case_node.case_id): {
                        "case_node_id": case_node.id,
                        "source": tmp_source[1:],
                        "result": result,
                    }
                }
            )
            
            if test_stat_info.get(result):
                test_stat_info.update({result: test_stat_info.get(result) + 1})
            else:
                test_stat_info.update({result: 1})
        else:
            tmp_source = source + "," + str(case_node.id)
            if not case_node.children.all():
                return
            for case_node_tmp in case_node.children.all():
                HandlerUpdateTaskProgress.get_case_node(
                    case_node_tmp, case_node_infos, all_node_ids, test_stat_info, tmp_source
                )

    @collect_sql_error
    def get_task_case_node(self):
        """
        :description: Get all child case_nodes under the version task
        :return: 
            case_node_infos: dict, store all child case_node whose type is case under the case_node
            all_node_ids: list, store all child case_node ids under the case_node
        """
        case_node = CaseNode.query.filter_by(id=self.task.case_node_id).first()
        HandlerUpdateTaskProgress.get_case_node(
            case_node, self.all_task_case_node_infos, self.all_node_ids, self.all_task_test_static_info
        )

    @staticmethod
    def get_all_tasks(task, task_ids):
        """
        获取所有测试任务
        """
        task_ids.append(task.id)
        for sub_task in task.children.filter(Task.is_delete.is_(False)).all():
            HandlerUpdateTaskProgress.get_all_tasks(
                sub_task,
                task_ids
            )
