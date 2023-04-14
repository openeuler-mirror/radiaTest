# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2022-04-12 14:05:57
import json

from flask import jsonify, current_app, g
from flask_restful import Resource
import sqlalchemy
from flask_pydantic import validate

from server import casbin_enforcer
from server.model import Pmachine, IMirroring, Vmachine
from server.model.pmachine import MachineGroup
from server.model.permission import ReScopeRole, Role, Scope
from server.utils.db import Edit, collect_sql_error, Delete
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


class MachineGroupEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
    def post(self, body: MachineGroupCreateSchema):
        return ResourceManager("machine_group").add_v2(
            "pmachine/api_infos.yaml",
            body.__dict__
        )

    @auth.login_required
    @response_collect
    @workspace_error_collect
    @validate()
    def get(self, workspace: str, query: MachineGroupQuerySchema):
        return ResourcePoolHandler.get_all(query, workspace)


class MachineGroupItemEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
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
    def delete(self, machine_group_id):
        return ResourcePoolHandler.delete_group(machine_group_id)

    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    def get(self, machine_group_id):
        return ResourcePoolHandler.get(machine_group_id)


class MachineGroupHeartbeatEvent(Resource):
    @collect_sql_error
    @validate()
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
    def delete(self, pmachine_id):
        return ResourceManager("pmachine").del_cascade_single(
            pmachine_id, Vmachine, [Vmachine.pmachine_id == pmachine_id], False)

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
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
    def put(self, pmachine_id, body: PmachineOccupySchema):
        return PmachineOccupyReleaseHandler.occupy_with_bind_scopes(
            pmachine_id, 
            body
        )


class PmachineReleaseEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The pmachine does not exist. Please check."
            )
        if pmachine.state == "idle":
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Pmachine state has not been modified. Please check."
            )
        if pmachine.state == "occupied" and pmachine.description \
                == current_app.config.get("CI_HOST"):
            vmachine = Vmachine.query.filter_by(pmachine_id=pmachine.id).first()
            if vmachine:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="Pmachine has vmmachine, can't released."
                )

        # 修改随机密码
        _body = {
            "id": pmachine.id,
            "ip": pmachine.ip,
            "user": pmachine.user,
            "port": pmachine.port,
            "old_password": pmachine.password,
            "random_flag": True,
        }

        if pmachine.description in [current_app.config.get("CI_HOST"),
                                    current_app.config.get("CI_PURPOSE")]:
            _body.update(
                {
                    "random_flag": False
                }
            )

        if _body.get("random_flag"):
            _resp = PmachineMessenger(_body).send_request(
                pmachine.machine_group,
                "/api/v1/pmachine/ssh",
            )

            _resp = json.loads(_resp.data.decode('UTF-8'))
            if _resp.get("error_code") != RET.OK:
                return jsonify(
                    error_code=RET.BAD_REQ_ERR,
                    error_msg="Modify ssh password error, can't released."
                )
            else:
                messenger_res = _resp.get("error_msg")
                current_app.logger.info("messenger response info:{}".format(messenger_res))
                pmachine_passwd = _resp.get("data")
                if isinstance(pmachine_passwd, list):
                    mail = Mail()
                    mail.send_text_mail(
                        current_app.config.get("ADMIN_MAIL_ADDR"),
                        subject="【radiaTest平台】{}-密码变更通知".format(pmachine_passwd[0]),
                        text="{} new password:{}".format(pmachine_passwd[0], pmachine_passwd[1])
                    )
                else:
                    return jsonify(
                        error_code=RET.BAD_REQ_ERR,
                        error_msg="messenger response is not correct"
                    )
        if pmachine.state == "occupied":
            _body = {
                "description": sqlalchemy.null(),
                "occupier": sqlalchemy.null(),
                "start_time": sqlalchemy.null(),
                "end_time": sqlalchemy.null(),
                "state": "idle",
                "listen": sqlalchemy.null(),
            }

        _body.update({"id": pmachine_id})
        resp = Edit(Pmachine, _body).single(Pmachine, "/pmachine")
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp 

        # 删除权利
        if g.gitee_id != pmachine.creator_id:
            role = Role.query.filter_by(type='person', name=g.gitee_id).first()
            if not role:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The role policy info is invalid."
                )

            scope_occupy = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}/occupy'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_occupy:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_occupy policy info is invalid."
                )
            _occupy = ReScopeRole.query.filter_by(scope_id=scope_occupy.id, role_id=role.id).all()
            if not _occupy:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _occupy policy info is invalid."
                )

            scope_release = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}/release'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_release:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_release policy info is invalid."
                )
            _release = ReScopeRole.query.filter_by(scope_id=scope_release.id, role_id=role.id).all()
            if not _release:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _release policy info is invalid."
                )

            scope_install = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}/install'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_install:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_install policy info is invalid."
                )
            _install = ReScopeRole.query.filter_by(scope_id=scope_install.id, role_id=role.id).all()
            if not _install:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _install policy info is invalid."
                )

            scope_power = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}/power'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_power:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_power policy info is invalid."
                )
            _power = ReScopeRole.query.filter_by(scope_id=scope_power.id, role_id=role.id).all()
            if not _power:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _power policy info is invalid."
                )

            scope_update = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_update:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_update policy info is invalid."
                )
            _update = ReScopeRole.query.filter_by(scope_id=scope_update.id, role_id=role.id).all()
            if not _update:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _update policy info is invalid."
                )

            scope_ssh = Scope.query.filter_by(
                act='put',
                uri='/api/v1/pmachine/{}/ssh'.format(pmachine_id),
                eft='allow'
            ).first()
            if not scope_ssh:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The scope_ssh policy info is invalid."
                )
            _ssh = ReScopeRole.query.filter_by(scope_id=scope_ssh.id, role_id=role.id).all()
            if not _ssh:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The _ssh policy info is invalid."
                )
            for occ in _occupy:
                Delete(ReScopeRole, {"id": occ.id}).single()
            for rea in _release:
                Delete(ReScopeRole, {"id": rea.id}).single()
            for ins in _install:
                Delete(ReScopeRole, {"id": ins.id}).single()
            for powe in _power:
                Delete(ReScopeRole, {"id": powe.id}).single()
            for upd in _update:
                Delete(ReScopeRole, {"id": upd.id}).single()
            for ssh in _ssh:
                Delete(ReScopeRole, {"id": ssh.id}).single()
        
        return jsonify(error_code=RET.OK, error_msg="OK")

        

class PmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @collect_sql_error
    @validate()
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
    def get(self, workspace: str, query: PmachineQuerySchema):
        return PmachineHandler.get_all(query, workspace)


class PmachineBmcEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
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
                "id": pmachine_id,
                "bmc_ip": pmachine.bmc_ip,
                "bmc_user": pmachine.bmc_user,
                "port": pmachine.port,
                "old_bmc_password": pmachine.bmc_password,
            }
        )
        return PmachineMessenger(_body).send_request(
            pmachine.machine_group,
            "/api/v1/pmachine/bmc",
        )


class PmachineSshEvent(Resource):
    @auth.login_required
    @response_collect
    @casbin_enforcer.enforcer
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
    def put(self, pmachine_id, body: PmachineInstallSchema):
        pmachine = Pmachine.query.filter_by(
            id=pmachine_id
        ).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the machine does not exist"
            )

        machine_group = pmachine.machine_group
        messenger = PmachineMessenger(body.__dict__)
        messenger.send_request(machine_group, "/api/v1/pmachine/check-bmc-info")

        imirroring = IMirroring.query.filter_by(
            milestone_id=body.milestone_id
        ).first()
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
                "mirroring": imirroring.to_json()
            }
        )

        messenger = PmachineMessenger(_body)
        return messenger.send_request(machine_group, "/api/v1/pmachine/install")


class Power(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
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
