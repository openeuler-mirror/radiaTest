from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate
from messenger.utils.response_util import RET
from messenger.apps.pmachine.handlers import AutoInstall, OnOff
from messenger.schema.pmachine import (
    PmachineInstallSchema,
    PmachinePowerSchema,
    PmachineBaseSchema,
    PmachineEventSchema,
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


class CheckBmcInfo(Resource):
    @validate()
    def put(self, body: PmachineBaseSchema):
        _body = body.__dict__
        _body.update({
            "auth": request.headers.get("authorization")
        })

        return jsonify(
            error_code=RET.OK, 
            error_msg="succeed in check bmc info."
        )

class CheckPmachineInfo(Resource):
    @validate()
    def put(self, body: PmachineEventSchema):
        _body = body.__dict__
        _body.update({
            "auth": request.headers.get("authorization")
        })

        return jsonify(
            error_code=RET.OK,
            error_msg="succeed in check bmc info and pmachine info."
        )