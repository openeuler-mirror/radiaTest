from flask import request, jsonify
from flask_restful import Resource

from worker.apps.vmachine.handle import (
    # InstallVmachine,
    domain_cli,
    domain_state,
    attach_device,
    OperateVmachine,
    OperateVdisk,
    OperateVnic,
)

from celeryservice.tasks import *


class VmachineEvent(Resource):
    def post(self):
        body = request.json
        _task = create_vmachine.delay(body)
        return jsonify(
            error_code="2000", 
            error_msg="OK", 
            data={"tid": _task.task_id}
        )

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
