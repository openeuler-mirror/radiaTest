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

from flask import current_app

from server.model.baselinetemplate import BaseNode
from server.model.testcase import CaseNode
from server import db, redis_client
from celeryservice.lib import TaskHandlerBase


class ResolveBaseNodeHandler(TaskHandlerBase):
    def create_base_node(self, body: dict):
        parent = BaseNode.query.get(body.get("parent_id"))
        if not parent:
            return

        case_node_ids = body.pop("case_node_ids")
        for case_node_id in case_node_ids:
            case_node = CaseNode.query.filter(
                CaseNode.id == case_node_id,
                CaseNode.type == body.get("type"),
            ).first()
            if not case_node:
                current_app.logger.warn(
                    f"case node #{case_node_id} dose not exist,"
                    f"base node relates failed"
                )
                continue
            #加锁，避免异步任务重复添加数据
            case_node_key = f"CREATE_CASE_NODE_F_{parent.title}_S_{case_node.title}"
            if redis_client.keys(case_node_key):
                continue
            redis_client.hmset(
                case_node_key,
                {
                    "user_id": body.get("creator_id")
                }
            )
            redis_client.expire(case_node_key, 300)
            base_node = BaseNode(
                creator_id=body.get("creator_id"),
                group_id=body.get("group_id"),
                org_id=body.get("org_id"),
                baseline_template_id=body.get("baseline_template_id"),
                permission_type=body.get("permission_type"),
                type=body.get("type"),
                title=case_node.title,
                case_node_id=case_node.id,
                is_root=False
            )
            db.session.add(base_node)
            db.session.commit()
            base_node.parent.append(parent)
            base_node.add_update()
            redis_client.delete(case_node_key)