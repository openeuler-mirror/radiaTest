# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2022-04-12 14:05:57
import json
import datetime

from flask import request, jsonify, current_app, Response
from flask_restful import Resource
import sqlalchemy
from flask_pydantic import validate

from server import casbin_enforcer
from server.model import Pmachine, IMirroring, Vmachine
from server.model.pmachine import MachineGroup
from server.utils.db import Edit, Select, collect_sql_error
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.utils.resource_utils import ResourceManager
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
)
from .handlers import PmachineHandler, PmachineMessenger, ResourcePoolHandler


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
    @validate()
    def get(self, query: MachineGroupQuerySchema):
        return ResourcePoolHandler.get_all(query)


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
                error_code = RET.NO_DATA_ERR,
                error_msg = "The pmachine does not exist. Please check."
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
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code = RET.NO_DATA_ERR,
                error_msg = "The pmachine does not exist. Please check."
            )
        if pmachine.state == "occupied":
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "Pmachine state has not been modified. Please check."
            )
        _body = body.__dict__
        _body.update({
            "id": pmachine_id,
            "state": "occupied",
        })
        
        return Edit(Pmachine, _body).single(Pmachine, "/pmachine")    


class PmachineReleaseEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, pmachine_id):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code = RET.NO_DATA_ERR,
                error_msg = "The pmachine does not exist. Please check."
            )
        if pmachine.state == "idle":
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "Pmachine state has not been modified. Please check."
            )
        if pmachine.state == "occupied" and pmachine.description == current_app.config.get("CI_HOST"):
            vmachine = Vmachine.query.filter_by(pmachine_id=pmachine.id).first()
            if vmachine:
                return jsonify(
                    error_code = RET.NO_DATA_ERR,
                    error_msg = "Pmachine has vmmachine, can't released."
                )
        if pmachine.state == "occupied":
            _body = {
                    "description": "",
                    "occupier": "",
                    "start_time": sqlalchemy.null(),
                    "end_time": sqlalchemy.null(),
                    "state": "idle",
                    "listen": None,
            }

        _body.update({"id": pmachine_id})

        return Edit(Pmachine, _body).single(Pmachine, "/pmachine")


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
    @validate()
    def get(self, query: PmachineQuerySchema):
        return PmachineHandler.get_all(query)


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


class PmachineDelayEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
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
