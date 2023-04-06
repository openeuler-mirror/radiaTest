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

from flask import current_app, jsonify, request, g

from server.model.product import Product
from server.model.milestone import Milestone
from server.model.testcase import Suite, CaseNode
from server.utils.db import Insert, Precise
from server.utils.resource_utils import ResourceManager
from server.utils.response_util import ssl_cert_verify_error_collect, RET
from server.utils.requests_util import do_request


class UpdateTaskForm:
    def __init__(self, body):
        self.body = body.__dict__
        self.product_id = None
        self.milestone_id = None
        self.title = None
        self.group = None


class UpdateTaskHandler:
    @staticmethod
    def get_product_id(form: UpdateTaskForm):
        version = form.body.get("version")
        product_body = {
            "name": form.body.get("product"),
            "version": version
        }
        _product = Precise(Product, product_body).first()

        if not _product:
            if "LTS-SP" in version:
                version_type = "LTS-SPx"
            elif "LTS" in version:
                version_type = "LTS"
            else:
                version_type = "INNOVATION"
            product_body.update(
                {
                    "permission_type": "org",
                    "org_id": form.group.org_id,
                    "version_type": version_type
                }
            )
            form.product_id = Insert(
                Product,
                product_body
            ).insert_id()

            ResourceManager("product", creator_id=form.group.creator_id, org_id=form.group.org_id).add_permission(
                "api_infos.yaml",
                {
                    "creator_id": form.group.creator_id,
                    "org_id": form.group.org_id,
                    "permission_type": "org",
                },
                form.product_id,
            )
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
                "creator_id": form.group.creator_id,
                "group_id": form.group.id,
                "org_id": form.group.org_id
            }
            form.milestone_id = Insert(
                Milestone,
                body
            ).insert_id()
            ResourceManager("milestone", creator_id=form.group.creator_id, org_id=form.group.org_id).add_permission(
                "api_infos.yaml",
                {
                    "creator_id": form.group.creator_id,
                    "org_id": form.group.org_id,
                    "permission_type": "org",
                },
                form.milestone_id,
            )
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
        for suite in form.body.get("pkgs"):
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
            self.content += "[{}]\nname={}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(
                result[-1],
                result[-1],
                self._base_url
            )

        if self._epol_url:
            rs = result[-1].split("_")[-1]
            self.content += "[EPOL-UPDATE-{}]\nname=EPOL-UPDATE-{}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n". \
                format(rs, rs, self._epol_url)


class AtMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": g.user_id,
        })

    @ssl_cert_verify_error_collect
    def send_request(self, machine_group, api):
        _resp = dict()

        _r = do_request(
            method="post",
            url="https://{}:{}{}".format(
                machine_group.messenger_ip,
                machine_group.messenger_listen,
                api
            ),
            body=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": request.headers.get("authorization")
            },
            obj=_resp,
            verify=current_app.config.get("CA_CERT"),
        )

        if _r != 0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(_resp)
