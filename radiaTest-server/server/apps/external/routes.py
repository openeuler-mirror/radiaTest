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
import json
import requests

from flask import current_app, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.schema.external import LoginOrgListSchema, OpenEulerUpdateTaskBase, VmachineExistSchema
from server.model.group import Group
from server.model.mirroring import Repo
from server.model.vmachine import Vmachine
from server.utils.db import Insert, Edit
from .handler import UpdateRepo, UpdateTaskHandler, UpdateTaskForm
from server.model.organization import Organization
from server.utils.response_util import RET
from server.utils.requests_util import gen_path_by_protocol


class UpdateTaskEvent(Resource):
    @validate()
    def post(self, body: OpenEulerUpdateTaskBase):
        form = UpdateTaskForm(body)

        # get group_id
        groups = Group.query.all()
        _group = list(filter(lambda x: x.name == current_app.config.get("OE_QA_GROUP_NAME"), groups))

        if not _group:
            return {"error_code": RET.TASK_WRONG_GROUP_NAME, "error_msg": "invalid group name by openEuler QA config"}
        
        group = _group[0]

        # get product_id
        UpdateTaskHandler.get_product_id(form)

        # extract update milestone name
        pattern = r'/(update.+?)/'

        result = re.findall(pattern, body.base_update_url)

        if  not result:
            return {"error_code": RET.WRONG_INSTALL_WAY, "error_msg": "invalid repo url format"}

        form.title = "{} {} {}".format(
            body.product,
            body.version,
            result[-1]
        )

        # get milestone_id
        UpdateTaskHandler.get_milestone_id(form)

        # get cases
        UpdateTaskHandler.suites_to_cases(form)

        #create repo config content
        update_repo = UpdateRepo(body)
        update_repo.create_repo_config()

        # insert or update repo config and use internal task execute api
        for frame in ["aarch64", "x86_64"]:
            repo = Repo.query.filter_by(
                milestone_id=form.milestone_id, 
                frame=frame
            ).first()

            if not repo:
                Insert(
                    Repo, 
                    {
                        "content": update_repo.content, 
                        "frame": frame, 
                        "milestone_id": form.milestone_id
                    }
                ).single(Repo, "/repo")
            else:
                Edit(
                    Repo,
                    {
                        "id": repo.id,
                        "content": update_repo.content, 
                    }
                ).single(Repo, "/repo")

            _verify = True if current_app.get("CA_VERIFY") == "True" else False

            requests.post(
                url="https://{}/api/v1/tasks/execute".format(
                    current_app.config.get("SERVER_ADDR")
                ),
                data=json.dumps({
                    "title": "{} {}".format(form.title, frame),
                    "milestone_id": form.milestone_id,
                    "group_id": group.id,
                    "frame": frame,
                    "cases": form.cases,
                }),
                headers=current_app.config.get("HEADERS"),
                verify=_verify,
            )
            
        # return response
        return {"error_code": RET.OK, "error_msg": "OK"}


class LoginOrgList(Resource):
    def get(self):
        return_data = []
        orgs = Organization.query.filter_by(is_delete=False).all()
        for org in orgs:
            org_dict = LoginOrgListSchema(**org.__dict__).__dict__
            org_dict.update({
                "cla": True if org.cla_verify_url else False,
                "enterprise": True if org.enterprise_id else False,
            })
            return_data.append(org_dict)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK", 
            data=return_data
        )


class VmachineExist(Resource):
    @validate()
    def get(self, query: VmachineExistSchema):
        vmachine = Vmachine.query.filter_by(name=query.domain).first()
        if not vmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="vmachine does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vmachine.name
        )