# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : hukun66
# @email   : hu_kun@hoperun.com
# @Date    : 2023/09/04
# @License : Mulan PSL v2
#####################################

import json

from flask import jsonify, current_app, g
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer, swagger_adapt
from server.model import Pmachine, IMirroring, Vmachine
from server.model.pmachine import MachineGroup
from server.utils.db import Edit, collect_sql_error
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET, workspace_error_collect
from server.utils.resource_utils import ResourceManager
from server.utils.mail_util import Mail
from server.schema.pmachine import (
    MachineGroupCreateSchema,
    MachineGroupQuerySchema,
    MachineGroupUpdateSchema,
    PmachineCreateSchema,
    PmachineQuerySchema,
    PmachineUpdateSchema,
    PmachineInstallSchema,
    PmachinePowerSchema,
    HeartbeatUpdateSchema,
    PmachineDelaySchema,
    PmachineOccupySchema,
    PmachineSshSchema,
    PmachineBmcSchema,
)
from .handlers import PmachineHandler, PmachineMessenger, PmachineOccupyReleaseHandler, ResourcePoolHandler


def get_pmachine_tag():
    return {
        "name": "物理机",
        "description": "物理机相关接口",
    }


class MachineGroupEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "创建机器组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": MachineGroupCreateSchema,
    })
    def post(self, body: MachineGroupCreateSchema):
        return ResourceManager("machine_group").add_v2(
            "pmachine/api_infos.yaml",
            body.__dict__
        )

    @auth.login_required
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "分页查询机器组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": MachineGroupQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, workspace: str, query: MachineGroupQuerySchema):
        return ResourcePoolHandler.get_all(query, workspace)


class MachineGroupItemEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "编辑机器组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": MachineGroupUpdateSchema,
    })
    def put(self, machine_group_id, body: MachineGroupUpdateSchema):
        machine_group = MachineGroup.query.filter_by(id=machine_group_id).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The machine group does not exist"
            )

        _body = body.__dict__
        _body.update({"id": machine_group_id})

        return Edit(MachineGroup, _body).single(MachineGroup, "/machine_group")

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除机器组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, machine_group_id):
        return ResourcePoolHandler.delete_group(machine_group_id)

    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取机器组信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, machine_group_id):
        return ResourcePoolHandler.get(machine_group_id)


class MachineGroupHeartbeatEvent(Resource):
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MachineGroupHeartbeatEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "更新机器组心跳",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": HeartbeatUpdateSchema,
    })
    def put(self, body: HeartbeatUpdateSchema):
        machine_group = MachineGroup.query.filter_by(messenger_ip=body.messenger_ip).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine group does not exist"
            )

        _body = {
            "id": machine_group.id,
            **body.__dict__,
        }

        return Edit(MachineGroup, _body).single(MachineGroup, "/machine_group")


class PmachineItemEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "删除物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, pmachine_id):
        return ResourceManager("pmachine").del_cascade_single(
            pmachine_id, Vmachine, [Vmachine.pmachine_id == pmachine_id], False)

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取物理机信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the pmachine does not exist",
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=pmachine.to_public_json()
        )

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "编辑物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineUpdateSchema,
    })
    def put(self, pmachine_id, body: PmachineUpdateSchema):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The pmachine does not exist. Please check."
            )
        _body = body.__dict__
        _body.update({"id": pmachine_id})

        return Edit(Pmachine, _body).single(Pmachine, "/pmachine")


class PmachineOccupyEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineOccupyEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "占用物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineOccupySchema,
    })
    def put(self, pmachine_id, body: PmachineOccupySchema):
        pmachine_handler = PmachineOccupyReleaseHandler()
        return pmachine_handler.occupy_with_bind_scopes(pmachine_id, body)


class PmachineReleaseEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineReleaseEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "释放物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The pmachine does not exist. Please check."
            )
        pmachine_handler = PmachineOccupyReleaseHandler()
        return pmachine_handler.release_with_release_scopes(pmachine)


class PmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "注册物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineCreateSchema
    })
    def post(self, body: PmachineCreateSchema):
        machine_group = MachineGroup.query.filter_by(id=body.machine_group_id).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine group of this machine does not exist"
            )

        messenger = PmachineMessenger(body.__dict__)
        resp = messenger.send_request(machine_group, "/api/v1/pmachine/check-machine-info")

        try:
            result = json.loads(resp.text).get("data")
        except AttributeError:
            if isinstance(resp, dict):
                return resp
            result = resp.json.get("data")

        if not result.get("status"):
            return resp

        _body = body.__dict__
        _body.update({"status": result.get("status")})

        return ResourceManager("pmachine").add("api_infos.yaml", _body)

    @auth.login_required
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "分页查询物理机",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": PmachineQuerySchema
    })
    def get(self, workspace: str, query: PmachineQuerySchema):
        return PmachineHandler.get_all(query, workspace)


class PmachineBmcEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineBmcEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取物理机bmc信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the pmachine does not exist",
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=pmachine.to_bmc_json()
        )

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineBmcEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改物理机bmc密码",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineBmcSchema
    })
    def put(self, pmachine_id, body: PmachineBmcSchema):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The pmachine does not exist."
            )
        if body.bmc_password == pmachine.bmc_password:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The bmc_password of pmachine does not modify."
            )
        _body = body.__dict__
        _body.update(
            {
                "bmc_ip": pmachine.bmc_ip,
                "bmc_user": pmachine.bmc_user,
                "old_bmc_password": pmachine.bmc_password,
                "bmc_password": body.bmc_password
            }
        )
        _resp = PmachineMessenger(_body).send_request(
            pmachine.machine_group,
            "/api/v1/pmachine/bmc",
        )
        _resp = json.loads(_resp.data.decode('UTF-8'))
        if _resp.get("error_code") != RET.OK:
            resp_msg = _resp.get("error_msg")
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=f"Modify bmc password error, can't update db data.the reason is:{resp_msg}"
            )
        else:
            pmachine.bmc_password = body.bmc_password
            pmachine.add_update()
            mail = Mail()
            mail.send_text_mail(
                current_app.config.get("ADMIN_MAIL_ADDR"),
                subject="【radiaTest平台】{}-bmc密码变更通知".format(pmachine.bmc_ip),
                text="{} new bmc password:{}".format(pmachine.bmc_ip, body.bmc_password)
            )
            return jsonify(
                error_code=RET.OK,
                error_msg="Modify bmc password success"
            )


class PmachineSshEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineSshEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "获取物理机系统用户和密码",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the pmachine does not exist",
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=pmachine.to_ssh_json()
        )

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineSshEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "修改物理机系统用户和密码",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineSshSchema
    })
    def put(self, pmachine_id, body: PmachineSshSchema):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The pmachine does not exist."
            )
        if body.password == pmachine.password:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The password of pmachine does not modify."
            )
        _body = body.__dict__
        _body.update(
            {
                "id": pmachine.id,
                "ip": pmachine.ip,
                "user": pmachine.user,
                "port": pmachine.port,
                "old_password": pmachine.password,
            }
        )
        return PmachineMessenger(_body).send_request(
            pmachine.machine_group,
            "/api/v1/pmachine/ssh",
        )


class PmachineDelayEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PmachineDelayEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "物理机延期",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineDelaySchema
    })
    def put(self, pmachine_id, body: PmachineDelaySchema):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if pmachine.end_time is None:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Lack of end_time of pmachine."
            )
        _body = body.__dict__
        _body.update(
            {
                "id": pmachine_id
            }
        )
        return Edit(Pmachine, _body).single(Pmachine, "/pmachine")


class Install(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Install",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "物理机自动化安装",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachineInstallSchema
    })
    def put(self, pmachine_id, body: PmachineInstallSchema):
        pmachine = Pmachine.query.filter_by(
            id=pmachine_id
        ).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine does not exist"
            )

        imirroring = IMirroring.query.filter_by(milestone_id=body.milestone_id, frame=pmachine.frame).order_by(
            IMirroring.update_time.desc(), IMirroring.id.desc()).first()
        if not imirroring:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the iso mirror of this milestone does not exist"
            )
        _body = body.__dict__
        _body.update(
            {
                "id": pmachine_id,
                "pmachine": pmachine.to_json(),
                "mirroring": imirroring.to_json(),
                "milestone_name": imirroring.milestone.name,
                "os_info": {"name": imirroring.milestone.product.name, "version": imirroring.milestone.product.version},
                "user_id": g.user_id,
            }
        )

        messenger = PmachineMessenger(_body)
        return messenger.send_request(pmachine.machine_group, "/api/v1/pmachine/install")


class Power(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_pmachine_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Power",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_pmachine_tag(),  # 当前接口所对应的标签
        "summary": "物理机上下电",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": PmachinePowerSchema
    })
    def put(self, pmachine_id, body: PmachinePowerSchema):
        pmachine = Pmachine.query.filter_by(
            id=pmachine_id
        ).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine does not exist"
            )

        machine_group = pmachine.machine_group
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine group of this machine does not exist"
            )
        _body = body.__dict__
        _body.update(
            {
                "id": pmachine_id,
                "pmachine": pmachine.to_json()
            }
        )
        messenger = PmachineMessenger(_body)
        messenger.send_request(machine_group, "/api/v1/pmachine/check-bmc-info")

        messenger = PmachineMessenger(_body)
        return messenger.send_request(machine_group, "/api/v1/pmachine/power")
