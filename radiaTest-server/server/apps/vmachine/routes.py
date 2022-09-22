# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/20
# @License : Mulan PSL v2
#####################################

import json
import string
import random
from flask import current_app, request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate
from server.apps.vmachine.handlers import (
    VmachineHandler,
    search_device,
    VmachineForceHandler,
    VmachineMessenger
)
from server.model.pmachine import Pmachine, MachineGroup
from server.model.milestone import Milestone
from server.schema.vmachine import (
    DeviceBaseSchema,
    DeviceDeleteSchema,
    PowerSchema,
    VdiskCreateSchema,
    VdiskUpdateSchema,
    VmachineCreateSchema,
    VmachineDataCreateSchema,
    VmachineDataUpdateSchema,
    VmachineDelaySchema,
    VmachinePreciseQuerySchema,
    VmachineQuerySchema,
    VnicBaseSchema,
    VnicCreateSchema,
    VmachineIpaddrSchema,
    VmachineItemUpdateSchema,
    VmachineBatchCreateSchema,
)
from server.utils.auth_util import auth
from server.utils.db import Delete, Edit, Insert
from server.utils.response_util import attribute_error_collect, response_collect, RET
from server.model import Vmachine, Vdisk, Vnic
from server.utils.permission_utils import PermissionManager, GetAllByPermission
import os
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer
from server.utils.callback_auth_util import callback_auth
from server import redis_client


class VmachineItemEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    @casbin_enforcer.enforcer
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
    @casbin_enforcer.enforcer
    def get(self, vmachine_id):
        vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
        if not vmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the vmachine does not exist"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vmachine.to_public_json()
        )

    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    def put(self, vmachine_id, body: VmachineItemUpdateSchema):
        vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group

        _body = body.__dict__
        _body.update(
            {
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json(),
                "name": vmachine.name
            }
        )

        return VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vmachine/{}".format(vmachine_id),
            "put",
        )


class PreciseVmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def get(self, query: VmachinePreciseQuerySchema):
        return GetAllByPermission(Vmachine).precise(query.__dict__)


class VmachineBatchDelayEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self):
        _body = request.json
        return Edit(Vmachine, _body).batch(Vmachine, "/vmachine")


class VmachineEvent(Resource):
    def __init__(self, body=None) -> None:
        super().__init__()
        self.body = body

    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: VmachineCreateSchema):
        if not body.capacity:
            body.capacity = current_app.config.get("VM_DEFAULT_CAPACITY")
        _milestone = Milestone.query.filter_by(id=body.milestone_id).first()
        _product_id = _milestone.product_id

        update_milestone = None
        if _milestone.type == "update":
            _update_milestone = _milestone

            _milestone = Milestone.query.filter_by(
                product_id=_product_id,
                type="release"
            ).first()

        if self.body:
            _body = self.body.__dict__
        else:
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

        resp = VmachineMessenger(_body).send_request(
            machine_group,
            "/api/v1/vmachine",
            "post",
        )
        resp_analyse = json.loads(resp.data.decode('UTF-8'))
        if resp_analyse.get("error_code") == RET.OK and body.method in ["auto", "import"]:
            redis_client.set(
                body.name,
                request.headers.get("authorization"),
                ex=current_app.config.get("CALLBACK_EXPIRE_TIME")
            )
        return resp

    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: VmachineQuerySchema):
        return VmachineHandler.get_all(query)

    @auth.login_required
    @response_collect
    @validate()
    def delete(self):
        vmachine_list = request.json.get("id")
        return VmachineHandler.delete(vmachine_list)


class VmachineBatchEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: VmachineBatchCreateSchema):
        des = body.description
        name = body.name
        names = []
        try:
            for i in range(body.count):
                body.description = (des + "_" + str(i))
                body.name = (name + str(i) + "-"
                             + "".join(
                            random.choice(string.ascii_lowercase + string.digits)
                            for _ in range(3)))

                obj = VmachineEvent(body)
                obj.post()
                names.append(body.name)

        except RuntimeError:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the vmachines creation failed."
            )
        return jsonify(
            data=names,
            error_code=RET.OK,
            error_msg="OK."
        )


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
                "pmachine": pmachine.to_json(),
                "vmachine": vmachine.to_json(),

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


class VmachineIpaddrItem(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, vmachine_id, body: VmachineIpaddrSchema):
        _body = body.__dict__
        _body.update(
            {
                "id": vmachine_id,
            }
        )
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine")


class VmachineItemForceEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, vmachine_id):
        return VmachineForceHandler.delete(vmachine_id)


class VmachineSshEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def get(self, vmachine_id):
        vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
        if not vmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the vmachine does not exist"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=vmachine.to_ssh_json()
        )


class AttachDevice(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    def post(self, body: DeviceBaseSchema):
        vmachine = Vmachine.query.filter_by(id=body.vmachine_id).first()
        pmachine = vmachine.pmachine
        machine_group = pmachine.machine_group
        resps = []
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
            resps,
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
        _body = body.__dict__
        _body.update({"id": vmachine_id})
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine", True)

    @auth.login_required
    @response_collect
    def delete(self, vmachine_id):
        return ResourceManager("vmachine").del_single(vmachine_id)


class VnicData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: VnicCreateSchema):
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
        _body = body.__dict__
        _body.update({"id": vnic_id})
        return Edit(Vnic, _body).single(Vnic, "/vnic", True)

    @auth.login_required
    @response_collect
    def delete(self, vnic_id):
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
        _body = body.__dict__
        _body.update({"id": vdisk_id})
        return Edit(Vdisk, _body).single(Vdisk, "/vdisk", True)

    @auth.login_required
    @response_collect
    def delete(self, vdisk_id):
        return Delete(
            Vdisk,
            {
                "id": vdisk_id
            }
        ).single(Vdisk, "/vdisk", True)


class VmachineStatusEvent(Resource):
    @validate()
    def put(self):
        _body = request.get_json()
        domains_run = dict()
        domains_shut_off = dict()

        if len(_body.get("domains_run").get("domain")) != 0:
            domains_run.update(_body.get("domains_run"))
            Edit(Vmachine, domains_run).batch_update_status(Vmachine, "/vmachine", True)

        if len(_body.get("domains_shut_off").get("domain")) != 0:
            domains_shut_off.update(_body.get("domains_shut_off"))
            Edit(Vmachine, domains_shut_off).batch_update_status(Vmachine, "/vmachine", True)

        return jsonify(
            error_code=RET.OK,
            error_msg="vmachines status update success:{},{}".format(
                _body.get("domains_run"),
                _body.get("domains_shut_off")
            )
        )


class VmachineCallBackEvent(Resource):
    @callback_auth
    @response_collect
    def put(self, vmachine_id):
        _body = request.get_json()
        _body.update({"id": vmachine_id})
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine", True)
