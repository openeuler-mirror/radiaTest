from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Pmachine
from server.utils.db import Insert, Delete, Edit, Select, collect_sql_error
from server.utils.auth_util import auth
from server.utils.response_util import response_collect, RET
from server.utils.permission_utils import PermissionItemsPool
from server.apps.pmachine.handlers import AutoInstall, OnOff
from server.schema.base import DeleteBaseModel
from server.schema.pmachine import (
    PmachineBase,
    PmachineUpdate,
    PmachineInstall,
    PmachinePower,
)

class PmachineEventItem(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def delete(self, pmachine_id):
        return Delete(Pmachine, {"id":pmachine_id}).single(Pmachine, "/pmachine")
    
    @auth.login_required
    @response_collect
    @validate()
    def get(self, pmachine_id):
        return Select(Pmachine, {"id":pmachine_id}).single()

class PmachineEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: PmachineBase):
        return Insert(Pmachine, body.__dict__).single(Pmachine, "/pmachine")

    @auth.login_required
    @response_collect
    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Pmachine, body.__dict__).batch(Pmachine, "/pmachine")

    @auth.login_required
    @response_collect
    @validate()
    def put(self, body: PmachineUpdate):
        body = body.__dict__
        if body.get("state"):
            if body.get("state") == "idle":
                body["occupier"]= None

            return Edit(Pmachine, body).pmachine(Pmachine, "/pmachine")
        
        return Edit(Pmachine, body).single(Pmachine, "/pmachine")

    @auth.login_required
    @response_collect
    @validate()
    def get(self):
        body = request.args.to_dict()
        return Select(Pmachine, body).fuzz()


class Install(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, body: PmachineInstall):
        return AutoInstall(body.__dict__).kickstart()


class Power(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def put(self, body: PmachinePower):
        return OnOff(body.__dict__).on_off()
