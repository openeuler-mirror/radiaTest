from flask import request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer
from server.apps.vmachine.handlers import (
    CreateVmachine,
    DeleteVmachine,
    Control,
    DeviceManager,
    VmachineAsyncResultHandler,
    search_device,
    ForceDeleteVmachine,
)
from server.model.pmachine import Pmachine
from server.schema.base import DeleteBaseModel
from server.schema.vmachine import (
    VdiskBase,
    VmachineBase,
    Power,
    VnicBase,
    Vdisk,
    DeviceDelete,
    DeviceBase,
    VmachineDelay
)
from server.utils.auth_util import auth
from server.utils.db import Edit, Like, Select
from server.model import Vmachine, Vdisk, Vnic


class VmachineEventItem(Resource):
    @validate()
    def delete(self, vmachine_id):
        return DeleteVmachine({"id":vmachine_id}).run()

    @validate()
    def get(self, vmachine_id):
        return Select(Vmachine, {"id":vmachine_id}).single()

class VmachineEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: VmachineBase):
        body.pm_select_mode = "auto"
        return CreateVmachine(body.__dict__).install()

    @auth.login_required
    @validate()
    def delete(self, body: DeleteBaseModel):
        return DeleteVmachine(body.__dict__).run()

    # @validate()
    # def put(self, body: EditBaseModel):
    #     return EditVmachine(body.__dict__).work()

    @validate()
    def get(self):
        body = request.args.to_dict()
        if body.get("host_ip"):
            results = []
            hosts = Like(Pmachine, {"ip": body.get("host_ip")}).all()
            if not hosts:
                return jsonify([])
            for host in hosts:
                body.update({"pmachine_id": host.id})
                result = Select(Vmachine, body).fuzz()
                if result:
                    results = results + result.json
            return jsonify(list(set(results)))
        return Select(Vmachine, body).fuzz()

class VmachineCallbackEvent(Resource):
    def put(self):
        body = request.json
        return VmachineAsyncResultHandler.edit(body)


class VmachineControl(Resource):
    @validate()
    def put(self, body: Power):
        return Control(body.__dict__).run()

class VmachineDelayEvent(Resource):
    @validate()
    def put(self, vmachine_id, body: VmachineDelay):
        body.id = vmachine_id
        return Edit(Vmachine, body.__dict__).single(Vmachine, "/vmachine")

class VmachineEventItemForce(Resource):
    @validate()
    def delete(self, vmachine_id):
        return ForceDeleteVmachine({"id":[vmachine_id]}).run()

class AttachDevice(Resource):
    @validate()
    def post(self, body: DeviceBase):
        return DeviceManager(body.__dict__, None, "virtual/machine/attach").attach()


class VnicEvent(Resource):
    @validate()
    def post(self, body: VnicBase):
        return DeviceManager(body.__dict__, None, "virtual/machine/vnic").add(Vnic)

    @validate()
    def delete(self, body: DeviceDelete):
        return DeviceManager(body.__dict__, None, "virtual/machine/vnic").delete(Vnic)

    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vnic)


class VdiskEvent(Resource):
    @validate()
    def post(self, body: VdiskBase):
        return DeviceManager(body.__dict__, None, "virtual/machine/vdisk").add(Vdisk)

    @validate()
    def delete(self, body: DeviceDelete):
        return DeviceManager(body.__dict__, None, "virtual/machine/vdisk").delete(Vdisk)

    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vdisk)
