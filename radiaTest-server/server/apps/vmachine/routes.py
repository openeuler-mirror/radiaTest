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
import os
import string
import random
import time

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
from server.utils.response_util import attribute_error_collect, response_collect, RET, workspace_error_collect
from server.model import Vmachine, Vdisk, Vnic
from server.utils.permission_utils import PermissionManager, GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer, swagger_adapt
from server.utils.callback_auth_util import callback_auth
from server import redis_client
from server.utils.vmachine_util import EditVmachine


def get_vmachine_tag():
    return {
        "name": "虚拟机",
        "description": "虚拟机相关接口",
    }


class VmachineItemEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取虚拟机信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改虚拟机信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineItemUpdateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PreciseVmachineEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "精确查询虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": VmachinePreciseQuerySchema
    })
    def get(self, workspace: str, query: VmachinePreciseQuerySchema):
        return GetAllByPermission(Vmachine, workspace).precise(query.__dict__)


class VmachineBatchDelayEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineBatchDelayEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机批量延期",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "创建虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineCreateSchema
    })
    def post(self, body: VmachineCreateSchema):
        if not body.capacity:
            body.capacity = current_app.config.get("VM_DEFAULT_CAPACITY")
        _milestone = Milestone.query.filter_by(id=body.milestone_id).first()
        _product_id = _milestone.product_id

        _update_milestone = None
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
        if _update_milestone:
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

        frame_number = _body.pop("frame_number")
        for item in frame_number:
            for num in range(item.get("machine_num")):
                _body.update({
                    "frame": item.get("frame"),
                    "name": (
                            time.strftime("%y-%m-%d-")
                            + str(time.time())
                            + "-"
                            + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
                    )
                })

                resp = VmachineMessenger(_body).send_request(
                    machine_group,
                    "/api/v1/vmachine",
                    "post",
                )

        return resp

    @auth.login_required
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "分页查询虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": VmachineQuerySchema
    })
    def get(self, workspace: str, query: VmachineQuerySchema):
        return VmachineHandler.get_all(query, workspace)

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "批量删除虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model":  [{
            "name": "id",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "虚拟机id列表",
            "schema": {'type': "array", 'items': {"type": "integer"}}}
        ]
    })
    def delete(self):
        vmachine_list = request.json.get("id")
        return VmachineHandler.delete(vmachine_list)


class VmachineBatchEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineBatchEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "批量创建虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineBatchCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineControl",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机上下电",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PowerSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineDelayEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机延期",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineDelaySchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineIpaddrItem",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机ip修改",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineIpaddrSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemForceEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机强制删除",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, vmachine_id):
        return VmachineForceHandler.delete(vmachine_id)


class VmachineSshEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineSshEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取虚拟机ssh信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "AttachDevice",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机附加设备",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": DeviceBaseSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机创建vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VnicCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机删除vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DeviceDeleteSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取虚拟机所有vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求参数
        "query_schema_model": [{
            "name": "vmachine_id",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "虚拟机id",
            "schema": {"type": "integer"}}],
    })
    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vnic)


class VdiskEvent(Resource):
    @auth.login_required
    @response_collect
    @attribute_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机vdisk创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VdiskCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机删除vdisk",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DeviceDeleteSchema
    })
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

    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机获取vdisk",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": [{
            "name": "vmachine_id",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "虚拟机id",
            "schema": {"type": "integer"}}],
    })
    def get(self):
        body = request.args.to_dict()
        return search_device(body, Vdisk)


class VmachineData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineData",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "创建虚拟机数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineDataCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemData",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VmachineDataUpdateSchema
    })
    def put(self, vmachine_id, body: VmachineDataUpdateSchema):
        _body = body.__dict__
        _body.update({"id": vmachine_id})
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine", True)

    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineItemData",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, vmachine_id):
        return ResourceManager("vmachine").del_single(vmachine_id)


class VnicData(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicData",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "创建虚拟机vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VnicCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicItemData",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改虚拟机vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VnicBaseSchema
    })
    def put(self, vnic_id, body: VnicBaseSchema):
        _body = body.__dict__
        _body.update({"id": vnic_id})
        return Edit(Vnic, _body).single(Vnic, "/vnic", True)

    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VnicItemData",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除虚拟机vnic",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskData",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机vdisk创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VdiskCreateSchema
    })
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskItemData",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改虚拟机vdisk",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": VdiskUpdateSchema
    })
    def put(self, vdisk_id, body: VdiskUpdateSchema):
        _body = body.__dict__
        _body.update({"id": vdisk_id})
        return Edit(Vdisk, _body).single(Vdisk, "/vdisk", True)

    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VdiskItemData",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除虚拟机vdisk",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, vdisk_id):
        return Delete(
            Vdisk,
            {
                "id": vdisk_id
            }
        ).single(Vdisk, "/vdisk", True)


class VmachineStatusEvent(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineStatusEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "批量修改虚拟机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self):
        _body = request.get_json()
        vmachines_name = list(_body.keys())

        if len(_body) != 0:
            EditVmachine(Vmachine, _body).batch_update_status(Vmachine, vmachines_name, "/vmachine", True)

        return jsonify(
            error_code=RET.OK,
            error_msg="vmachines status update success:{}".format(_body)
        )


class VmachineCallBackEvent(Resource):
    @auth.login_required
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_vmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "VmachineCallBackEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_vmachine_tag(),  # 当前接口所对应的标签
        "summary": "虚拟机回调接口，更新数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": swagger_adapt.get_request_schema_by_db_model(Vmachine)
    })
    def put(self, vmachine_id):
        _body = request.get_json()
        _body.update({"id": vmachine_id})
        if _body.get("ip"):
            vmachine = Vmachine.query.filter_by(ip=_body.get("ip")).first()
            if vmachine:
                _body.pop("ip")
        return Edit(Vmachine, _body).single(Vmachine, "/vmachine", True)
