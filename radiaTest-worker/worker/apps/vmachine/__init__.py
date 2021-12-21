# -*- coding: utf-8 -*-
# @Author : lemon-higgins
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Date   : 2021-11-02 17:16:43


import time

from flask import request, jsonify
from flask_restful import Resource

from worker.apps.vmachine.handle import (
    InstallVmachine,
    domain_cli,
    domain_state,
    attach_device,
    OperateVmachine,
    OperateVdisk,
    OperateVnic,
)


class VmachineEvent(Resource):
    def post(self):
        body = request.json

        if body.get("method") == "auto":
            return InstallVmachine(body).kickstart()
        elif body.get("method") == "import":
            return InstallVmachine(body)._import()
        elif body.get("method") == "cdrom":
            return InstallVmachine(body).cd_rom()
        else:
            return jsonify({"error_code": 30010, "error_mesg": "未提供正确的安装方式."})

    def put(self):
        pass

    def delete(self):
        return OperateVmachine(request.json).delete()


class VmachinePower(Resource):
    def put(self):
        body = request.json

        exitcode, status = domain_state(body.get("name"))

        exitcode, output = domain_cli(body.get("status"), body.get("name"))
        if exitcode:
            return jsonify({"error_code": exitcode, "error_mesg": output})

        while [True]:
            exitcode, output = domain_state(body.get("name"))
            if output in ["running", "shut off", "paused"] and output != status:
                break

        exitcode, output = domain_state(body.get("name"))
        if exitcode:
            return jsonify({"error_code": exitcode, "error_mesg": output})

        return jsonify({"status": output})


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
