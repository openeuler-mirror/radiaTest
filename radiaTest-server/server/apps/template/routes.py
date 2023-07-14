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
# @Date    : 2023-05-24
# @License : Mulan PSL v2
#####################################

import json
from datetime import datetime
import pytz
from flask import request, jsonify, g
from flask_restful import Resource
from flask_pydantic import validate

from server.model.template import Template
from server.model.testcase import Case
from server.utils.db import Edit
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect, workspace_error_collect
from server.schema.template import TemplateUpdate, TemplateCloneBase, TemplateCreateByimportFile
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer
from server.apps.template.handler import TemplateCaseImportHandler


class TemplateEvent(Resource):
    @auth.login_required()
    @response_collect
    def post(self):
        _form = dict()
        for key, value in request.form.items():
            if value:
                _form[key] = value

        body = TemplateCreateByimportFile(**_form)
        template = Template.query.filter_by(name=body.name).first()
        if template:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="the template exists")

        if request.files.get("file") and request.form.get("cases"):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg=f"file and cases cannot exist at the same time"
            )
        elif request.files.get("file"):
            _filetype = request.files.get("file").filename.split(".")[-1]
            if _filetype not in ["xls", "csv", "xlsx", "json"]:
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg=f"Filetype of {_filetype} not supported"
                )

            try:
                import_handler = TemplateCaseImportHandler(
                    request.files.get("file"))
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR,
                    error_msg=str(e),
                )
            _body = body.__dict__
            _ = ResourceManager("template").add("api_infos.yaml", _body)
            import_handler.import_case(
                {
                    "name": body.name,
                    "git_repo_id": body.git_repo_id
                }
            )
        elif request.form.get("cases"):
            _body = body.__dict__
            _ = ResourceManager("template").add("api_infos.yaml", _body)
            try:
                cases = map(int, request.form.get("cases").split(','))
            except ValueError:
                return jsonify(error_code=RET.PARMA_ERR, error_msg="cases param error.")
            template = Template.query.filter_by(name=body.name).first()
            TemplateCaseImportHandler.add_template_cases(
                template=template,
                cases=cases
            )
        return jsonify(error_code=RET.OK, error_msg="OK")

    @auth.login_required
    @response_collect
    @workspace_error_collect
    def get(self, workspace: str):
        body = request.args.to_dict()
        return GetAllByPermission(Template, workspace).fuzz(body)


class TemplateItemEvent(Resource):
    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def put(self, template_id):
        template = Template.query.filter_by(id=template_id).first()
        if not template:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="the template doesn't exist")

        if request.form.get("name"):
            _template = Template.query.filter_by(
                name=request.form.get("name")).first()
            if _template and _template.id != template_id:
                return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="the template name exists")

        _form = dict()
        for key, value in request.form.items():
            if value:
                _form[key] = value
        body = TemplateUpdate(**_form)
        _body = body.__dict__
        for key, value in _body.items():
            setattr(template, key, value)
        template.add_update()

        if request.files.get("file") and request.form.get("cases"):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg=f"file and cases cannot exist at the same time"
            )
        elif request.files.get("file"):
            _filetype = request.files.get("file").filename.split(".")[-1]
            if _filetype not in ["xls", "csv", "xlsx", "json"]:
                return jsonify(
                    error_code=RET.PARMA_ERR,
                    error_msg=f"Filetype of {_filetype} not supported"
                )

            try:
                import_handler = TemplateCaseImportHandler(
                    request.files.get("file")
                )
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR,
                    error_msg=str(e),
                )
            TemplateCaseImportHandler.remove_template_cases(template)

            import_handler.import_case(
                {
                    "name": template.name,
                    "git_repo_id": template.git_repo_id
                }
            )
        elif request.form.get("cases"):
            try:
                cases = map(int, request.form.get("cases").split(','))
            except ValueError:
                return jsonify(error_code=RET.PARMA_ERR, error_msg="cases param error.")
            TemplateCaseImportHandler.update_template_cases(
                template=template,
                cases=cases
            )
        return jsonify(error_code=RET.OK, error_msg="OK")

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

    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    def delete(self, template_id):
        return ResourceManager("template").del_single(template_id)


class TemplateCloneEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: TemplateCloneBase):
        _template = Template.query.filter_by(id=body.id).first()
        if not _template:
            raise RuntimeError("the selected template does not exist.")
        _nowstr = datetime.now(
            tz=pytz.timezone('Asia/Shanghai')
        ).strftime("%Y-%m-%d-%H-%M-%S")
        _body = {
            "name": _template.name + _nowstr,
            "description": _template.description + _nowstr if _template.description else _nowstr,
            "milestone_id": _template.milestone_id,
            "git_repo_id": _template.git_repo_id,
            "permission_type": body.permission_type,
            "creator_id": g.user_id,
            "group_id": body.group_id,
            "org_id": _template.org_id,
        }

        resp = ResourceManager("template").add("api_infos.yaml", _body)

        template = Template.query.filter_by(
            name=_template.name + _nowstr
        ).first()

        for case in _template.cases:
            template.cases.append(case)

        template.add_update(Template, "/template")

        return resp
