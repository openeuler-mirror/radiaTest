# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 14:30:29
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.model import Pmachine
from server.utils.db import Insert, Delete, Edit, Select
from server.apps.pmachine.handlers import AutoInstall, OnOff
from server.schema.base import DeleteBaseModel
from server.schema.pmachine import (
    PmachineBase,
    PmachineUpdate,
    PmachineInstall,
    PmachinePower,
)


class PmachineEvent(Resource):
    @validate()
    def post(self, body: PmachineBase):
        return Insert(Pmachine, body.__dict__).single(Pmachine, "/pmachine")

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Pmachine, body.__dict__).batch(Pmachine, "/pmachine")

    @validate()
    def put(self, body: PmachineUpdate):
        body = body.__dict__
        if body.get("state"):
            if body.get("state") == "idle":
                body["occupier"]= None

            return Edit(Pmachine, body).pmachine(Pmachine, "/pmachine")
        
        return Edit(Pmachine, body).single(Pmachine, "/pmachine")

    @validate()
    def get(self):
        body = request.args.to_dict()
        return Select(Pmachine, body).fuzz()


class Install(Resource):
    @validate()
    def put(self, body: PmachineInstall):
        return AutoInstall(body.__dict__).kickstart()


class Power(Resource):
    @validate()
    def put(self, body: PmachinePower):
        return OnOff(body.__dict__).on_off()
