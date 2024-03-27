# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author :
# @Email  :
# @License: Mulan PSL v2
# @Date   : 2022-12-20 13:46:29
#####################################

import os
from flask import jsonify, g
from server import db, redis_client
from server.model.task import (
    TaskDistributeTemplate,
    DistributeTemplateType,
    Task,
    TaskMilestone,
)
from server.model.testcase import Suite
from server.model.group import ReUserGroup
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.utils.redis_util import RedisKey
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import get_api

base_dir = os.path.dirname(os.path.abspath(__file__))


class HandlerTemplate:
    @staticmethod
    @collect_sql_error
    def get(query):
        if hasattr(g, "user_id"):
            org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
            rugs = ReUserGroup.query.filter_by(
                user_id=g.user_id,
                org_id=org_id,
                is_delete=False,
                user_add_group_flag=True,
            ).all()
            groups = [item.group_id for item in rugs]
        else:
            groups = []

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

        def page_func(item):
            data_dict = item.to_simple_json()
            return data_dict

        return PageUtil.get_data(
            query_filter=query_filter,
            query=query,
            func=page_func if query.simple else None
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
                dtt.suite_source = item.suite_source
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
        dtt.suite_source = body.suite_source
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
        PermissionManager.clean(
            "/api/v1/tasks/distribute-templates/types/", [type_id]
        )
        return jsonify(error_code=RET.OK, error_msg="OK")


class HandlerTaskDistributeCass:
    @collect_sql_error
    def distribute(self, task_id, template_id, body):
        from celeryservice.tasks import resolve_distribute_template
        task = Task.query.get(task_id)
        if not task or not task.group_id or task.type == "PERSON":
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task can not use template distribute cases",
            )
        task_milestone = TaskMilestone.query.filter_by(
            task_id=task_id, milestone_id=body.get("milestone_id")
        ).first()
        if not task_milestone:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task milestone relationship no find",
            )
        template = TaskDistributeTemplate.query.get(template_id)
        if template.group_id != task.group_id:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="task group not match template group",
            )
        task_key = f"DISTRIBUTE_TEMPLATE_{template_id}_TASK_{task_id}"
        _key = redis_client.keys(task_key)
        if _key:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="Assigning tasks according to template, please wait several minutes.",
            )
        body.update(
            {
                "base_dir": base_dir,
                "creator_id": g.user_id
            }
        )
        resolve_distribute_template.delay(
            task_id, template_id, body
        )

        return jsonify(error_code=RET.OK, error_msg="OK")
