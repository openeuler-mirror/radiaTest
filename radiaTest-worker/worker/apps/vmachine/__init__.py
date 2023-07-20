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

from flask import request, jsonify
from flask_restful import Resource

from worker.apps.vmachine.handlers import (
    domain_cli,
    domain_state,
    attach_device,
    OperateVmachine,
    OperateVdisk,
    OperateVnic,
)
from worker.config.settings import Config
from celeryservice.tasks import *


class VmachineEvent(Resource):
    def post(self):
        body = request.json
        auth = request.headers.get("authorization")

        _task = create_vmachine.delay(auth, body)
        return jsonify(
            error_code="2000", 
            error_msg="OK", 
            data={"tid": _task.task_id}
        )

    def put(self):
        return OperateVmachine(request.json).edit()

    def delete(self):
        return OperateVmachine(request.json).delete()


class VmachinePower(Resource):
    def put(self):
        body = request.json

        _, _ = domain_cli(body.get("status"), body.get("name"))

        exitcode, cur_status = domain_state(body.get("name"))

        if body.get("status") == "shutdown":
            cur_status = "shut off"

        if cur_status in ["running", "paused"] or body.get("status") == "start":
            vnc_port = int(domain_cli("vncdisplay", body.get("name"))[1].strip("\n").split(":")[-1])
            token_list = body.get("vnc_token").split("-")
            token_list[-1] = str(vnc_port + Config.VNC_START_PORT)
            vnc_token = ("-").join(token_list)
            return jsonify(
                {
                    "vnc_port": vnc_port,
                    "status": cur_status,
                    "vnc_token": vnc_token
                }
            )

        return jsonify({"status": cur_status})


class VnicEvent(Resource):
    def post(self):
        return OperateVnic(request.json).add()

    def delete(self):
        return OperateVnic(request.json).delete()


class VdiskEvent(Resource):
    def post(self):
        return OperateVdisk(request.json).add()

    def delete(self):
        return OperateVdisk(request.json).delete()

class AttachDevice(Resource):
    def post(self):
        body = request.json
        return attach_device(body.get("name"), body.get("xml"))
