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
from flask_restful import Resource
from flask_pydantic import validate
from server import casbin_enforcer
from server.schema.administrator import LoginSchema, RegisterSchema, ChangePasswdSchema
from server.schema.organization import AddSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.apps.administrator.handlers import (
    handler_login,
    handler_register,
    handler_read_org_list,
    handler_save_org,
    handler_update_org,
    handler_change_passwd
)


class Login(Resource):
    @validate()
    def post(self, body: LoginSchema):
        return handler_login(body)


class Register(Resource):
    @validate()
    def post(self, body: RegisterSchema):
        return handler_register(body)


class Org(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def get(self):
        return handler_read_org_list()

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def post(self):
        _form = dict()
        for key, value in request.form.items():
            if value:
                _form[key] = value

        body = AddSchema(**_form)
        avatar = request.files.get("avatar_url")
        return handler_save_org(body, avatar)


class OrgItem(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def put(self, org_id):
        return handler_update_org(org_id)


class ChangePasswd(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: ChangePasswdSchema):
        return handler_change_passwd(body)
