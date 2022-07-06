from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from messenger.apps.vmachine.handlers import (
    CreateVmachine,
    DeleteVmachine,
    Control,
    DeviceManager,
    VmachineAsyncResultHandler,
    EditVmachine,
    RequestWorkerParam,
    MachineInfoParam
)
from messenger.utils.response_util import runtime_error_collect
from messenger.schema.vmachine import (
    VdiskCreateSchema,
    VmachineBaseSchema,
    PowerSchema,
    VmachineItemSchema,
    VnicCreateSchema,
    DeviceDeleteSchema,
    DeviceBaseSchema,
    VmachineUpdateSchema,
)


class VmachineEventItem(Resource):
    @runtime_error_collect
    @validate()
    def delete(self, vmachine_id, body: VmachineItemSchema):
        _body = body.__dict__
        _body.update({"id": vmachine_id})
        auth = request.headers.get("authorization")
        return DeleteVmachine(auth, _body).run()

    @runtime_error_collect
    @validate()
    def put(self, vmachine_id, body: VmachineUpdateSchema):
        _body = body.__dict__
        _body.update({"id": vmachine_id})
        auth = request.headers.get("authorization")
        return EditVmachine(auth, _body).work()


class VmachineEvent(Resource):
    @runtime_error_collect
    @validate()
    def post(self, body: VmachineBaseSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        return CreateVmachine(auth, _body).install()


class VmachineCallbackEvent(Resource):
    @runtime_error_collect
    def put(self):
        body = request.json
        auth = request.headers.get("authorization")

        return VmachineAsyncResultHandler.edit(auth, body)


class VmachineControl(Resource):
    @runtime_error_collect
    @validate()
    def put(self, vmachine_id, body: PowerSchema):
        _body = body.__dict__
        _body.update({
            "id": vmachine_id,
        })
        auth = request.headers.get("authorization")

        return Control(auth, _body).run()


class AttachDevice(Resource):
    @runtime_error_collect
    @validate()
    def post(self, body: DeviceBaseSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        request_worker_param = RequestWorkerParam(
            auth,
            _body,
            "virtual/machine/attach"
        )
        machine_info_param = MachineInfoParam()

        return DeviceManager(request_worker_param, machine_info_param).attach()


class VnicEvent(Resource):
    @runtime_error_collect
    @validate()
    def post(self, body: VnicCreateSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        request_worker_param = RequestWorkerParam(
            auth,
            _body,
            "virtual/machine/vnic"
        )
        machine_info_param = MachineInfoParam()

        return DeviceManager(request_worker_param, machine_info_param).add("vnic")

    @validate()
    def delete(self, body: DeviceDeleteSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        request_worker_param = RequestWorkerParam(
            auth,
            _body,
            "virtual/machine/vnic"
        )
        machine_info_param = MachineInfoParam()

        return DeviceManager(request_worker_param, machine_info_param).delete("vnic")


class VdiskEvent(Resource):
    @validate()
    def post(self, body: VdiskCreateSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        request_worker_param = RequestWorkerParam(
            auth,
            _body,
            "virtual/machine/vdisk"
        )
        machine_info_param = MachineInfoParam()

        return DeviceManager(request_worker_param, machine_info_param).add("vdisk")

    @validate()
    def delete(self, body: DeviceDeleteSchema):
        _body = body.__dict__
        auth = request.headers.get("authorization")
        request_worker_param = RequestWorkerParam(
            auth,
            _body,
            "virtual/machine/vdisk"
        )
        machine_info_param = MachineInfoParam()

        return DeviceManager(request_worker_param, machine_info_param).delete("vdisk")
