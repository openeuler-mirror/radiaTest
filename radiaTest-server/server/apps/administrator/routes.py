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

from flask import request, current_app, jsonify, g
from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer, swagger_adapt
from server.schema.administrator import LoginSchema, ChangePasswdSchema, AddRuleSchema
from server.schema.organization import AddSchema, UpdateSchema
from server.utils.auth_util import auth
from server.utils.file_util import identify_file_type, FileTypeMapping
from server.utils.response_util import response_collect
from server.apps.administrator.handlers import (
    handler_login,
    handler_read_org_list,
    handler_save_org,
    handler_update_org,
    handler_change_passwd,
    check_authority
)
from server.model.administrator import Admin
from server.utils.page_util import PageUtil
from server.schema.base import PageBaseSchema
from server.utils.response_util import RET
from server.model.password_rule import PasswordRule
from server.utils.db import Insert, Delete


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
        result, form = check_authority(_form)
        if not result:
            return form
        body = AddSchema(**form)
        avatar = request.files.get("avatar_url")
        if avatar:
            # 文件头检查
            verify_flag, res = identify_file_type(avatar, FileTypeMapping.image_type)
            if verify_flag is False:
                return res
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


class PasswordRuleEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "PasswordRuleEvent",
        "func_name": "get",
        "tag": get_admin_tag(),
        "summary": "获取所有弱口令",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": PageBaseSchema
    })
    def get(self, query: PageBaseSchema):
        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to get rule')
            return resp
        query_filter = PasswordRule.query.filter()

        def page_func(item):
            password_rule = item.to_json()
            return password_rule

        page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(query_filter, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get password rule page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "PasswordRuleEvent",
        "func_name": "post",
        "tag": get_admin_tag(),
        "summary": "创建弱口令规则",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": AddRuleSchema
    })
    def post(self, body: AddRuleSchema):
        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to add rule')
            return resp

        rule_exists = PasswordRule.query.filter_by(rule=body.rule).first()
        if rule_exists:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="password rule already exists"
            )
        rule_id = Insert(PasswordRule, body.__dict__).insert_id()
        return jsonify(
            error_code=RET.OK,
            error_msg=f"add password rule[{rule_id}] success"
        )


class PasswordRuleItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "PasswordRuleItem",
        "func_name": "put",
        "tag": get_admin_tag(),
        "summary": "修改弱口令",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": AddRuleSchema
    })
    def put(self, rule_id, body: AddRuleSchema):
        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to delete rule')
            return resp

        rule_update = PasswordRule.query.filter_by(id=rule_id).first()
        if not rule_update:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="password rule not exists to update"
            )
        rule_update.rule = body.rule
        rule_update.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="password rule update success"
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_admin_tag.__module__,
        "resource_name": "PasswordRuleItem",
        "func_name": "delete",
        "tag": get_admin_tag(),
        "summary": "删除弱口令",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, rule_id):
        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to delete rule')
            return resp

        rule_exists = PasswordRule.query.filter_by(id=rule_id).first()
        if not rule_exists:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="password rule already not exists"
            )
        rule_exists.delete()
        return jsonify(
            error_code=RET.OK,
            error_msg=f"delete rule[{rule_id}] success"
        )
