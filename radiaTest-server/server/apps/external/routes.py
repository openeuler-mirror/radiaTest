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

import os
import re
import json
import shlex
from subprocess import getstatusoutput
import requests

from flask import current_app, jsonify, request, make_response, send_file
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer
from server.utils.auth_util import auth
from server.schema.external import (
    LoginOrgListSchema,
    OpenEulerUpdateTaskBase,
    VmachineExistSchema,
    DeleteCertifiSchema
)
from server.model.group import Group
from server.model.mirroring import Repo
from server.model.vmachine import Vmachine
from server.model.organization import Organization
from server.utils.db import Insert, Edit
from server.utils.response_util import RET, ssl_cert_verify_error_collect
from server.utils.file_util import ImportFile
from .handler import UpdateRepo, UpdateTaskHandler, UpdateTaskForm


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

        form.group = group
        # get product_id
        UpdateTaskHandler.get_product_id(form)

        # extract update milestone name
        pattern = r'/(update.+?)/'

        result = re.findall(pattern, body.base_update_url)

        if not result:
            return {"error_code": RET.WRONG_INSTALL_WAY, "error_msg": "invalid repo url format"}

        form.title = "{} {} {}".format(
            body.product,
            body.version,
            result[-1]
        )

        # get milestone_id
        UpdateTaskHandler.get_milestone_id(form)

        # get cases
        UpdateTaskHandler.create_case_node(form)

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


class CaCert(Resource):
    @auth.login_required()
    def get(self):
        return send_file(
            current_app.config.get("CA_CERT"),
            as_attachment=True
        )

    def post(self):
        _san = request.form.get("san")
        _messenger_ip = request.form.get("ip")
        _csr_file = request.files.get("csr")

        if not _messenger_ip or not _csr_file or not _san:
            return make_response(
                jsonify(
                    validation_error="lack of ip address/csr file/subject alternative name"
                ),
                current_app.config.get("FLASK_PYDANTIC_VALIDATION_ERROR_STATUS_CODE", 400)
            )

        csr_file = ImportFile(
            _csr_file,
            filename=request.form.get("ip"),
            filetype="csr"
        )

        try:
            csr_file.file_save(
                "{}/csr".format(
                    current_app.config.get("CA_DIR")
                ),
                timestamp=True,
            )
        except RuntimeError as e:
            return make_response(
                jsonify(
                    message=str(e)
                ),
                500
            )

        certs_dir = "{}/certs".format(
            current_app.config.get("CA_DIR")
        )
        if not os.path.exists(certs_dir):
            csr_file.file_remove()
            return make_response(
                jsonify(
                    message="the directory to storage certfile does not exist"
                ),
                500
            )

        certs_path = f"{certs_dir}/{_messenger_ip}.crt"

        caconf_path = "{}/conf/ca.cnf".format(current_app.config.get("CA_DIR"))

        exitcode, output = getstatusoutput(
            "bash server/apps/external/certs_sign.sh {} {} {} {}".format(
                shlex.quote(csr_file.filepath),
                shlex.quote(certs_path),
                caconf_path,
                shlex.quote(_san)
            )
        )

        if exitcode != 0:
            csr_file.file_remove()
            return make_response(
                jsonify(
                    message=f"fail to create certfile for machine group of messenger ip {_messenger_ip}: {output}"
                ),
                500
            )
        else:
            return send_file(certs_path, as_attachment=True)

    # @auth.login_required()
    # @casbin_enforcer.enforcer()
    @validate()
    def delete(self, body: DeleteCertifiSchema):

        exitcode, output = getstatusoutput(
            "openssl ca -revoke {0}/certs/{1}.crt -config {0}/openssl.cnf".format(
                current_app.config.get("CA_DIR"),
                body.ip,
            )
        )

        if exitcode != 0:
            raise RuntimeError(
                f"fail to delete certfile for machine group of messenger ip {body.ip}: {output}"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )