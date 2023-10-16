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

from flask import request, current_app
from flask_restful import Resource
from flask_pydantic import validate
from server import casbin_enforcer, swagger_adapt
from server.schema.administrator import LoginSchema, RegisterSchema, ChangePasswdSchema
from server.schema.organization import AddSchema, UpdateSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.apps.administrator.handlers import (
    handler_login,
    handler_register,
    handler_read_org_list,
    handler_save_org,
    handler_update_org,
    handler_change_passwd,
    check_authority
)


def get_admin_tag():
    return {
        "name": "管理员",
        "description": "管理员相关接口",
    }


class Login(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "Login",
        "func_name": "post",
        "tag": get_admin_tag(),
        "summary": "管理员登录",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": LoginSchema,
    })
    def post(self, body: LoginSchema):
        return handler_login(body)


class Register(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "Register",
        "func_name": "post",
        "tag": get_admin_tag(),
        "summary": "管理员注册",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": RegisterSchema,
    })
    def post(self, body: RegisterSchema):
        return handler_register(body)


class Org(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "Org",
        "func_name": "get",
        "tag": get_admin_tag(),
        "summary": "获取所有组织",
        "externalDocs": {"description": "", "url": ""},
    })
    def get(self):
        return handler_read_org_list()

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "Org",
        "func_name": "post",
        "tag": get_admin_tag(),
        "summary": "管理员创建组织",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": AddSchema
    })
    def post(self):
        _form = dict()
        for key, value in request.form.items():
            if value:
                _form[key] = value
        current_app.logger.info("register org:{}".format(_form))
        result, form = check_authority(_form)
        if not result:
            return form
        body = AddSchema(**form)
        avatar = request.files.get("avatar_url")
        return handler_save_org(body, avatar)


class OrgItem(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "OrgItem",
        "func_name": "put",
        "tag": get_admin_tag(),
        "summary": "管理员修改组织信息",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": UpdateSchema
    })
    def put(self, org_id):
        return handler_update_org(org_id)


class ChangePasswd(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "ChangePasswd",
        "func_name": "put",
        "tag": get_admin_tag(),
        "summary": "管理员修改密码",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": ChangePasswdSchema
    })
    def put(self, body: ChangePasswdSchema):
        return handler_change_passwd(body)
