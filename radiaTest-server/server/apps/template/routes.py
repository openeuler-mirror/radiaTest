# Copyright (c) [2021] Huawei Technologies Co.,Ltd.ALL rights reserved.
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

from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.model.template import Template
from server.model.testcase import Case
from server.utils.db import Insert, Edit, Select, Delete
from server.utils.auth_util import auth
from server.utils.response_util import RET
from server.schema.base import DeleteBaseModel
from server.schema.template import TemplateBase, TemplateUpdate


class TemplateEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: TemplateBase):
        _body = body.__dict__

        cases = []
        for case_id in _body.get("cases"):
            case = Case.query.filter_by(id=case_id).first()
            if not case:
                continue

            cases.append(case)

        _body.pop("cases")
        resp = Insert(Template, _body).single(Template, '/template')

        template = Template.query.filter_by(name=_body.get("name")).first()

        for case in cases:
            template.cases.append(case)

        template.add_update(Template, "/template")

        return resp

    @auth.login_required
    @validate()
    def put(self, body: TemplateUpdate):
        _body = body.__dict__

        cases = []
        for case_name in _body.get("cases"):
            cases.append(Case.query.filter_by(name=case_name).first())

        _body.pop("cases")
        resp = Edit(Template, _body).single(Template, '/template')
        template = Template.query.filter_by(name=_body.get("name")).first()

        for case in template.cases:
            template.cases.remove(case)
            template.add_update(Template, "/template")

        for case in cases:
            template.cases.append(case)
            template.add_update(Template, "/template")

        return resp

    @auth.login_required
    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Template, body.__dict__).batch(Template, "/template")

    @auth.login_required
    def get(self):
        body = request.args.to_dict()
        return Select(Template, body).precise()


class TemplateItemEvent(Resource):
    @auth.login_required
    def get(self, template_id):
        template = Template.query.filter_by(id=template_id).first()
        if not template:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="template not exist")
        
        vm_req_num = 0
        pm_req_num = 0
        for case in template.cases:
            if case.machine_type == "kvm":
                vm_req_num = max(vm_req_num, case.machine_num)
            elif case.machine_type == "physical":
                pm_req_num = max(vm_req_num, case.machine_num)

        return_data = template.to_json()
        return_data.update({
            "vm_req_num": vm_req_num,
            "pm_req_num": pm_req_num,
        })

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)