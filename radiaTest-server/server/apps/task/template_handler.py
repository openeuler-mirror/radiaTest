# -*- coding: utf-8 -*-
# @Author : gaodi12
# @Email  : gaodi12@huawei.com
# @License: Mulan PSL v2
# @Date   : 2021-12-20 13:46:29
import time
import pandas as pd
from flask import jsonify, g
from server import db, redis_client
from server.model.task import TaskDistributeTemplate, DistributeTemplateType, \
    Task, TaskStatus, TaskParticipant, TaskMilestone, TaskManualCase
from server.model.testcase import Suite, Case
from server.model.group import ReUserGroup
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.redis_util import RedisKey


class HandlerTemplate:
    @staticmethod
    @collect_sql_error
    def get(query):
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        rugs = ReUserGroup.query.filter_by(user_gitee_id=g.gitee_id, org_id=org_id, is_delete=False,
                                           user_add_group_flag=True).all()
        groups = [item.group_id for item in rugs]
        filter_params = [TaskDistributeTemplate.group_id.in_(groups)]
        if query.name:
            filter_params.append(TaskDistributeTemplate.name.like(f'%{query.name}%'))
        if query.group_id:
            filter_params.append(TaskDistributeTemplate.group_id == query.group_id)
        if query.type_name:
            filter_params.append(DistributeTemplateType.name.like(f'%{query.type_name}%'))
            query_filter = TaskDistributeTemplate.query.join(DistributeTemplateType).filter(*filter_params)
        else:
            query_filter = TaskDistributeTemplate.query.filter(*filter_params)
        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)

    @staticmethod
    @collect_sql_error
    def add(body):
        template = TaskDistributeTemplate(name=body.name, creator_id=g.gitee_id, group_id=body.group_id)
        if body.types:
            for item in body.types:
                dtt = DistributeTemplateType()
                dtt.name = item.name
                dtt.executor_id = item.executor_id
                dtt.creator_id = g.gitee_id
                dtt.suites = ','.join(item.suites)
                dtt.helpers = ','.join(item.helpers) if item.helpers else ''
                template.types.append(dtt)
        template.add_update()
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
        _ = [db.session.delete(item) for item in template.types]
        db.session.commit()
        db.session.delete(template)
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTemplateType:

    @staticmethod
    def get_all_suites(template: TaskDistributeTemplate):
        template_suites = []
        for item in template.types:
            template_suites = template_suites + item.suites.split(',') if item.suites else template_suites
        return template_suites

    @staticmethod
    @collect_sql_error
    def get(query):
        filter_params = [Suite.deleted.is_(False)]
        if query.template_id:
            template = TaskDistributeTemplate.query.get(query.template_id)
            template_suites = HandlerTemplateType.get_all_suites(template)
            filter_params.append(Suite.id.notin_(template_suites))
        query_filter = Suite.query.filter(*filter_params)
        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)

    @staticmethod
    @collect_sql_error
    def add(template_id, body):
        template = TaskDistributeTemplate.query.get(template_id)
        if body.name in [item.name for item in template.types]:
            return jsonify(error_code=RET.PARMA_ERR, error_msg='name has exists')
        dtt = DistributeTemplateType()
        dtt.name = body.name
        dtt.creator_id = g.gitee_id
        dtt.executor_id = body.executor_id
        dtt.suites = ','.join(body.suites)
        dtt.helpers = ','.join(body.helpers)
        template.types.append(dtt)
        template.add_update()
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
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskDistributeCass:

    def __init__(self):
        self.status = TaskStatus.query.filter_by(name="待办中").first()

    @collect_sql_error
    def distribute(self, task_id, template_id):
        # 分析数据
        # milestone_id, case_id, suite_id
        task = Task.query.get(task_id)
        if not task or not task.group_id or task.type == 'PERSON':
            return jsonify(error_code=RET.PARMA_ERR, error_msg='task can not use template distribute cases')
        task_cases = []
        for item in task.milestones:
            for case in item.cases:
                task_cases.append((item.milestone_id, case.id, case.suite_id))
        task_cases_df = pd.DataFrame(task_cases, columns=['milestone_id', 'case_id', 'suite_id'])
        # suite_id, executor_id, helpers, type_name
        template = TaskDistributeTemplate.query.get(template_id)
        if template.group_id != task.group_id:
            return jsonify(error_code=RET.PARMA_ERR, error_msg='task group not match template group')
        template_cases = []
        for item in template.types:
            for suite in item.suites.split(','):
                template_cases.append((int(suite), item.executor_id, item.helpers, item.name))
        template_cases_df = pd.DataFrame(template_cases, columns=['suite_id', 'executor_id', 'helpers', 'type_name'])
        merge_df = pd.merge(task_cases_df, template_cases_df, on='suite_id').reset_index(drop=True)
        if merge_df.empty:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg='no cases that can be assigned were found')
        for item in merge_df['type_name'].drop_duplicates().tolist():
            temp_df = merge_df[merge_df.type_name == item]
            temp_df = temp_df.reset_index(drop=True)
            self.create_child_task(task, temp_df, template.group_id)
        return jsonify(error_code=RET.OK, error_msg="OK")

    def create_child_task(self, parent_task: Task, df: pd.DataFrame, group_id):
        # milestone_id, case_id, suite_id, executor_id, helpers, type_name
        for milestone_id in df['milestone_id'].drop_duplicates().tolist():
            child_task = Task()
            child_task.title = f'T{parent_task.id}_TM{df.loc[0, "type_name"]}' \
                               f'_M{milestone_id}_S{time.strftime("%Y%m%d%H%M%S")}'
            child_task.type = 'GROUP'
            child_task.group_id = group_id
            child_task.originator = g.gitee_id
            child_task.start_time = parent_task.start_time
            child_task.executor_id = df.loc[0, "executor_id"]
            child_task.deadline = parent_task.deadline
            child_task.organization_id = parent_task.organization_id
            child_task.frame = parent_task.frame
            child_task.status_id = self.status.id
            child_task_id = child_task.add_flush_commit()
            child_task = Task.query.get(child_task_id)
            child_task.automatic = True
            if df.loc[0, 'helpers']:
                for item in df.loc[0, 'helpers'].split(','):
                    tp = TaskParticipant()
                    tp.task_id = child_task_id
                    tp.participant_id = item
                    child_task.participants.append(tp)

            tm = TaskMilestone()
            tm.task_id = child_task_id
            tm.milestone_id = milestone_id
            tm.cases = Case.query.filter(Case.id.in_(df[df.milestone_id == milestone_id]['case_id'].tolist()),
                                         Case.deleted.is_(False)).all()
            for case in tm.cases:
                if not case.automatic:
                    tmc = TaskManualCase(case_id=case.id)
                    child_task.automatic = False
                    tm.manual_cases.append(tmc)
            tm.add_update()
            child_task.add_update()
            # 父任务添加子任务
            parent_task.children.append(child_task)
        # 父任务删除测试用例
        for item in parent_task.milestones:
            self.delete_task_cases(item, df['case_id'].tolist())
        parent_task.add_update()

    @staticmethod
    def delete_task_cases(task_milestone: TaskMilestone, cases: list):
        tm_cases = task_milestone.cases.copy() if task_milestone.cases else []
        _ = [task_milestone.cases.remove(item) for item in tm_cases if item.id in cases]
        task_milestone.add_update()
        tm_manual_cases = task_milestone.manual_cases.copy() if task_milestone.manual_cases else []
        _ = [db.session.delete(item) for item in tm_manual_cases if item.case_id in cases]
        db.session.commit()
        automatic = True
        if not task_milestone.cases:
            automatic = False
        else:
            for item in task_milestone.cases:
                if not item.automatic:
                    automatic = False
                    break
        task_milestone.task.automatic = automatic
        task_milestone.task.add_update()
