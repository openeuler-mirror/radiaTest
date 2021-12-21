# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 16:19:53
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from flask import request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate
from server.apps.vmachine.handlers import (
    CreateVmachine,
    DeleteVmachine,
    Control,
    DeviceManager,
    search_device,
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
)

from server.utils.db import Like, Precise, Select

from server.model import Vmachine, Vdisk, Vnic


class VmachineEvent(Resource):
    @validate()
    def post(self, body: VmachineBase):
        return CreateVmachine(body.__dict__).install()

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


class VmachineControl(Resource):
    @validate()
    def put(self, body: Power):
        return Control(body.__dict__).run()


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
