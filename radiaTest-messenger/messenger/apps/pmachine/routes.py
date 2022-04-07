from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from messenger.apps.pmachine.handlers import AutoInstall, OnOff
from messenger.schema.pmachine import (
    PmachineInstallSchema,
    PmachinePowerSchema,
)


class Install(Resource):
    @validate()
    def put(self, body: PmachineInstallSchema):
        _body = body.__dict__
        _body.update({
            "auth": request.headers.get("authorization")
        })
        return AutoInstall(_body).kickstart()


class Power(Resource):
    @validate()
    def put(self, body: PmachinePowerSchema):
        _body = body.__dict__
        _body.update({
            "auth": request.headers.get("authorization")
        })
        return OnOff(_body).on_off()