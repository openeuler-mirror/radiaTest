# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from flask import request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from messenger.schema.job import RunSuiteBase, RunTemplateBase
from messenger.utils.response_util import RET
from celeryservice.tasks import run_suite, run_template


class RunSuiteEvent(Resource):
    @validate()
    def post(self, body: RunSuiteBase):
        _body = body.__dict__
        _user_id = _body.pop("user_id")

        _user = {
            "user_id": _user_id,
            "auth": request.headers.get("authorization"),
        }

        run_suite.delay(_body, _user)

        return jsonify(
            error_code=RET.OK, 
            error_msg="succeed in creating the job for running suite"
        )


class RunTemplateEvent(Resource):
    @validate()
    def post(self, body: RunTemplateBase):
        _body = body.__dict__
        _user_id = _body.pop("user_id")
        _user = {
            "user_id": _user_id,
            "auth": request.headers.get("authorization"),
        }
        run_template.delay(_body, _user)

        return jsonify(
            error_code=RET.OK, 
            error_msg="succeed in creating the job for running template"
        )
