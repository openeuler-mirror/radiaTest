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

from flask import request, jsonify
from flask_restful import Resource
from flask_pydantic import validate
from messenger.utils.response_util import RET
from messenger.apps.pmachine.handlers import (
    AutoInstall,
    OnOff,
    PmachineSshPassword,
    PmachineBmcPassword,
    PmachineInfo,
)
from messenger.schema.pmachine import (
    PmachineInstallSchema,
    PmachinePowerSchema,
    PmachineBaseSchema,
    PmachineEventSchema,
    PmachineSshSchema,
    PmachineBmcSchema,
    PmachineInfoSchema,
)


class Install(Resource):
    @validate()
    def put(self, body: PmachineInstallSchema):
        _body = body.__dict__
        # 前端触发安装执行celery任务
        return AutoInstall(_body).kickstart(is_async=True)


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
        return jsonify(
            data={
                "status": body.status
            },
            error_code=RET.OK,
            error_msg="succeed in check bmc info."
        )


class CheckPmachineInfo(Resource):
    @validate()
    def put(self, body: PmachineEventSchema):
        return jsonify(
            data={
                "status": body.status
            },
            error_code=RET.OK,
            error_msg="succeed in check bmc info and pmachine info."
        )


class PmachineSshItem(Resource):
    @validate()
    def put(self, body: PmachineSshSchema):
        _body = body.__dict__
        _body.update({
            "auth": request.headers.get("authorization")
        })
        return PmachineSshPassword(_body).reset_password()


class PmachineBmcItem(Resource):
    @validate()
    def put(self, body: PmachineBmcSchema):
        _body = body.__dict__
        return PmachineBmcPassword(_body).reset_bmc_password()


class AutoReleaseCheckPmachineEvent(Resource):
    @validate()
    def get(self, body: PmachineInfoSchema):
        _body = body.__dict__
        return PmachineInfo(_body).check()
