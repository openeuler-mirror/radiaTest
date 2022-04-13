from flask import request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer
from server.apps.vmachine.handlers import (
    VmachineHandler,
    search_device,
    VmachineForceHandler,
    VmachineMessenger
)
from server.model.pmachine import Pmachine, MachineGroup
from server.model.milestone import Milestone
from server.schema.base import DeleteBaseModel
from server.schema.vmachine import (
    DeviceBaseSchema,
    DeviceDeleteSchema,
    PowerSchema,
    VdiskBaseSchema,
    VdiskCreateSchema,
    VdiskUpdateSchema,
    VmachineCreateSchema,
    VmachineDataCreateSchema,
    VmachineDataUpdateSchema,
    VmachineDelaySchema,
    VmachinePreciseQuerySchema,
    VmachineQuerySchema,
    VnicBaseSchema,
    VdiskBaseSchema,
    VnicCreateSchema,
)
from server.utils.auth_util import auth
from server.utils.db import Delete, Edit, Like, Select, Insert
from server.utils.response_util import attribute_error_collect, response_collect, RET
from server.model import Vmachine, Vdisk, Vnic
from server.utils.permission_utils import PermissionManager, GetAllByPermission
import os
from server.utils.resource_utils import ResourceManager


class VmachineItemEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def delete(self, vmachine_id):
        _vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
        vmachine = _vmachine.to_json()
        pmachine = _vmachine.pmachine.to_json()
        machine_group = _vmachine.pmachine.machine_group

        return VmachineMessenger({
            "vmachine": vmachine,
            "pmachine": pmachine
        }).send_request(
            machine_group,
            "/api/v1/vmachine/{}".format(vmachine_id),
            "delete",
        )

    @auth.login_required
    @response_collect
    @validate()
    def get(self, vmachine_id):
        return Select(Vmachine, {"id":vmachine_id}).single()
    
    # @validate()
    # def put(self, vmachine_id, body: EditBaseModel):
    #     return EditVmachine(body.__dict__).work()


class PreciseVmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def get(self, query: VmachinePreciseQuerySchema):
        return GetAllByPermission(Vmachine).precise(query.__dict__)


class VmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: VmachineCreateSchema):
        _milestone = Milestone.query.filter_by(id=body.milestone_id).first()
        _product_id = _milestone.product_id

        update_milestone = None
        if _milestone.type == "update":
            _update_milestone = _milestone
        
        _milestone = Milestone.query.filter_by(
            product_id=_product_id,
            type="release"
        ).first()

        _body = body.__dict__

        _body.update(
            {
                "milestone": _milestone.to_json(),
                "product": _milestone.product.to_json(),
            }
        )
        if update_milestone:
            _body.update(
                {
                    "update_milestone": _update_milestone.to_json(),
                }
            )

        machine_group = None
        
        if body.pm_select_mode == "assign":
            pmachine = Pmachine.query.filter_by(id=body.pmachine_id).first()
            machine_group = pmachine.machine_group

            _body.update(
                {
                    "pmachine": pmachine.to_json()
                }
            )
        elif body.pm_select_mode == "auto":
            machine_group = MachineGroup.query.filter_by(
                id=body.machine_group_id
            ).first()
        
        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vmachine",
            "post",
        )

    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: VmachineQuerySchema):
        return VmachineHandler.get_all(query)

    @auth.login_required
    @response_collect
    @validate()
    def delete(self, body: DeleteBaseModel):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )
        return ResourceManager("vmachine").del_batch(body.__dict__.get("id"))


class VmachineControl(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def put(self, body: PowerSchema):
        vmachine = Vmachine.query.filter_by(id=body.id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json()
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vmachine/{}/power".format(body.id),
            "put",
        )


class VmachineDelayEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, vmachine_id, body: VmachineDelaySchema):
        _body = body.__dict__
        _body.update(
            {
                "id": vmachine_id
            }
        )
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine")


class VmachineItemForceEvent(Resource):
    @validate()
    def delete(self, vmachine_id):
        return VmachineForceHandler.delete(vmachine_id)


class AttachDevice(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: DeviceBaseSchema):
        vmachine = Vmachine.query.filter_by(id=body.vmachine_id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json()
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/attach",
            "post",
        )


class VnicEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: VnicCreateSchema):
        vmachine = Vmachine.query.filter_by(id=body.vmachine_id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json()
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vnic",
            "post",
        )
    
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def delete(self, body: DeviceDeleteSchema):
        vnic = Vnic.query.filter_by(id=body.id).first()
        vmachine = vnic.vmachine
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json(),
                "device": vnic.to_json()
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vnic",
            "delete",
        )

    @auth.login_required
    @response_collect
    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vnic)


class VdiskEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: VdiskCreateSchema):
        vmachine = Vmachine.query.filter_by(id=body.vmachine_id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json(),
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vdisk",
            "post",
        )

    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def delete(self, body: DeviceDeleteSchema):
        vdisk = Vdisk.query.filter_by(id=body.id).first()
        vmachine = vdisk.vmachine
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json(),
                "device": vdisk.to_json()
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vdisk",
            "delete",
        )

    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vdisk)


class VmachineData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: VmachineDataCreateSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        vmachine = Insert(Vmachine, body.__dict__).insert_obj(
            Vmachine, 
            "/vmachine", 
            True
        )
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split("/")[-1], "")
        allow_list, deny_list = PermissionManager().get_api_list("vmachine", cur_dir + "api_infos.yaml", vmachine.id)
        PermissionManager().generate(allow_list, deny_list, body.__dict__)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vmachine.to_json(),
        )


class VmachineItemData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, vmachine_id, body: VmachineDataUpdateSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        _body = body.__dict__
        _body.update({"id": vmachine_id})
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine", True)

    @auth.login_required
    @response_collect
    def delete(self, vmachine_id):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )
        
        return ResourceManager("vmachine").del_single(vmachine_id)


class VnicData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: VnicCreateSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        vnic = Insert(Vnic, body.__dict__).insert_obj(
            Vnic, 
            "/vnic", 
            True
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vnic.to_json(),
        )


class VnicItemData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, vnic_id, body: VnicBaseSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        _body = body.__dict__
        _body.update({"id": vnic_id})
        return Edit(Vnic, _body).single(Vnic, "/vnic", True)

    @auth.login_required
    @response_collect
    def delete(self, vnic_id):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        return Delete(
            Vnic, 
            {
                "id": vnic_id
            }
        ).single(Vnic, "/vnic", True)


class VdiskData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: VdiskCreateSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        vdisk = Insert(Vdisk, body.__dict__).insert_obj(
            Vdisk, 
            "/vdisk", 
            True
        )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vdisk.to_json(),
        )


class VdiskItemData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, vdisk_id, body: VdiskUpdateSchema):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        _body = body.__dict__
        _body.update({"id": vdisk_id})
        return Edit(Vdisk, _body).single(Vdisk, "/vdisk", True)

    @auth.login_required
    @response_collect
    def delete(self, vdisk_id):
        from_ip = request.remote_addr
        
        machine_group = MachineGroup.query.filter_by(ip=from_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="the api only serve for messenger service, make sure the request is from valid messenger service"
            )

        return Delete(
            Vdisk, 
            {
                "id": vdisk_id
            }
        ).single(Vdisk, "/vdisk", True)