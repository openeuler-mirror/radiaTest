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
import datetime

from flask import current_app

from server.model.product import Product
from server.model.milestone import Milestone
from server.model.testcase import Case, Suite, CaseNode
from server.model.group import ReUserGroup, GroupRole
from server.utils.db import Insert, Precise


class UpdateTaskForm:
    def __init__(self, body):
        self._body = body.__dict__
        self.product_id = None
        self.milestone_id = None
        self.title = None
        self.group = None


class UpdateTaskHandler:
    @staticmethod
    def get_product_id(form: UpdateTaskForm):
        product_body = {
            "name": form._body.get("product"),
            "version": form._body.get("version")
        }
        _product = Precise(Product, product_body).first()

        if not _product:
            product_body.update(
                {
                    "permission_type": "org",
                    "org_id": form.group.org_id
                }
            )
            form.product_id = Insert(
                Product,
                product_body
            ).insert_id()
        else:
            form.product_id = _product.id

    @staticmethod
    def get_milestone_id(form: UpdateTaskForm):
        _milestone = Milestone.query.filter_by(name=form.title).first()

        if not _milestone:
            body = {
                "name": form.title,
                "product_id": form.product_id,
                "type": "update",
                "is_sync": False,
                "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now() + datetime.timedelta(
                    days=current_app.config.get("OE_QA_UPDATE_TASK_PERIOD")
                )).strftime("%Y-%m-%d %H:%M:%S"),
                "permission_type": "org",
                "creator_id": ReUserGroup.query.filter_by(
                    group_id=form.group.id,
                    role_type=GroupRole.create_user.value
                ).first().user_gitee_id,
                "group_id": form.group.id,
                "org_id": form.group.org_id
            }
            form.milestone_id = Insert(
                Milestone,
                body
            ).insert_id()
        else:
            form.milestone_id = _milestone.id

    @staticmethod
    def create_case_node(form: UpdateTaskForm):
        milestone = Milestone.query.get(form.milestone_id)
        root_case_node_body = {
            "group_id": form.group.id,
            "title": milestone.name,
            "type": "directory",
            "milestone": milestone.id,
            "org_id": form.group.org_id,
            "permission_type": "group"
        }
        root_case_node = Precise(
            CaseNode, root_case_node_body).first()
        if not root_case_node:
            root_case_node = Insert(CaseNode, root_case_node_body).insert_obj()
        for suite in form._body.get("pkgs"):
            _suite = Suite.query.filter_by(name=suite).first()
            if not _suite:
                _suite = Insert(Suite, {"name": suite}).insert_obj()
            case_node_body = {
                "group_id": form.group.id,
                "title": _suite.name,
                "type": "suite",
                "suite_id": _suite.id,
                "org_id": form.group.org_id,
                "is_root": False,
                "permission_type": "group"
            }
            _ = Precise(Milestone, case_node_body).first()
            if not _:
                _ = Insert(CaseNode, case_node_body).insert_obj()
                root_case_node.children.append(_)
        root_case_node.add_update()


class UpdateRepo:
    def __init__(self, body) -> None:
        self._base_url = body.base_update_url
        self._epol_url = body.epol_update_url

        self.content = ""

    def create_repo_config(self):
        pattern = r'/(update.+?)/'
        result = re.findall(pattern, self._base_url)
        if self._base_url:
            self.content += "[{}]\nname={}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(result[-1], result[-1], self._base_url)
        
        if self._epol_url:
            rs = result[-1].split("_")[-1]
            self.content += "[EPOL-UPDATE-{}]\nname=EPOL-UPDATE-{}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(rs, rs, self._epol_url)
