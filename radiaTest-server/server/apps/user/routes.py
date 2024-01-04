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
from flask import Blueprint
from flask_restful import Resource
from flask_pydantic import validate

from server import swagger_adapt
from server import casbin_enforcer
from server.utils.cla_util import ClaSignSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.utils.register_auth import register_required
from server.schema.user import UserTaskSchema, UserMachineSchema, UserInfoSchema
from server.schema.user import OauthLoginSchema, LoginSchema, UpdateUserSchema, JoinGroupSchema, UserQuerySchema
from server.schema.user import UserCaseCommitSchema
from server.schema.base import PageBaseSchema
from .handlers import handler_oauth_callback
from .handlers import handler_oauth_login
from .handlers import handler_register
from .handlers import handler_update_user
from .handlers import handler_user_info
from .handlers import handler_logout
from .handlers import handler_select_default_org
from .handlers import handler_add_group
from .handlers import handler_get_all
from .handlers import handler_get_user_task
from .handlers import handler_get_user_machine
from .handlers import handler_login_callback
from .handlers import handler_get_user_case_commit
from .handlers import handler_get_user_asset_rank
from .handlers import handler_private



oauth = Blueprint('oauth', __name__)


def get_user_tag():
    return {
        "name": "用户",
        "description": "用户相关接口",
    }


@oauth.route("/api/v1/oauth/callback", methods=["GET"])
@swagger_adapt.api_schema_model_map({
    # 当前接口非Resource类，需要手动添加 url、method, 当前接口比较特殊，映射url为列表
    "url": ["/api/v1/oauth/callback"],
    "method": "get",  # 获取当前接口所在模块
    "__module__": get_user_tag.__module__,  # 获取当前接口所在模块
    "resource_name": "None",  # 当前接口视图函数名
    "func_name": "get",  # 当前接口所对应的函数名
    "tag": get_user_tag(),  # 当前接口所对应的标签
    "summary": "oauth回调接口",  # 当前接口概述
    "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    # 自定义请求参数
    "query_schema_model": [{
        "name": "code",
        "in": "query",
        "required": True,
        "style": "form",
        "explode": True,
        "description": "用户oauth code",
        "schema": {"type": "string"}},
        {
            "name": "user_id",
            "in": "cookie",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "用户id",
            "schema": {"type": "string"}}],
    # 自定义响应体
    "response_data_schema": {
            "302": {
                "description": "重定向到登录认证地址",
                "headers": {
                    "Location": {
                        "description": "重定向的位置",
                        "schema": {
                            "type": "string",
                            "format": "uri",
                        }}}}}
})
def oauth_callback():
    return handler_oauth_callback()


class OauthLogin(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "OauthLogin",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_user_tag(),  # 当前接口所对应的标签
        "summary": "oauth登录重定向",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": OauthLoginSchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: OauthLoginSchema):
        return handler_oauth_login(query)


class Login(Resource):
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "Login",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "登录回调接口",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": LoginSchema,
    })
    def get(self, query: LoginSchema):
        return handler_login_callback(query)


class User(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "User",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "搜索用户接口",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": UserQuerySchema,
    })
    def get(self, query: UserQuerySchema):
        return handler_get_all(query)


class UserItem(Resource):
    @register_required
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserItem",
        "func_name": "post",
        "tag": get_user_tag(),
        "summary": "用户注册接口",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": ClaSignSchema,
    })
    def post(self, user_id, body: ClaSignSchema):
        return handler_register(user_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserItem",
        "func_name": "put",
        "tag": get_user_tag(),
        "summary": "用户手机号更新接口",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": UpdateUserSchema,
    })
    def put(self, user_id, body: UpdateUserSchema):
        return handler_update_user(user_id, body)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserItem",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "获取用户信息接口",
        "externalDocs": {"description": "", "url": ""},
        "response_data_schema": UserInfoSchema,
    })
    def get(self, user_id):
        return handler_user_info(user_id)


class Logout(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "Logout",
        "func_name": "delete",
        "tag": get_user_tag(),
        "summary": "用户退出登录",
        "externalDocs": {"description": "", "url": ""},

    })
    def delete(self):
        return handler_logout()


class Org(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "Org",
        "func_name": "put",
        "tag": get_user_tag(),
        "summary": "选择默认组织",
        "externalDocs": {"description": "", "url": ""},
    })
    def put(self, org_id):
        return handler_select_default_org(org_id)


class Group(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "Group",
        "func_name": "put",
        "tag": get_user_tag(),
        "summary": "加入群组",
        "externalDocs": {"description": "", "url": ""},
        # 自定义请求体示例
        "request_schema_model": {
            "description": "",
            "content": {
                "application/json":
                    {"schema": {
                        "properties": {
                            "msg_id": {
                                "title": "消息id",
                                "type": "integer"
                            },
                            "access": {
                                "title": "是否接受",
                                "type": "boolean"
                            }
                        },
                        "required": ["msg_id", "access"],
                        "title": "JoinGroupSchema",
                        "type": "object"
                    }}
            },
            "required": True
        }

    })
    def put(self, group_id, body: JoinGroupSchema):
        return handler_add_group(group_id, body)


class UserTask(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserTask",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "获取用户任务列表",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": UserTaskSchema,
    })
    def get(self, query: UserTaskSchema):
        return handler_get_user_task(query)


class UserMachine(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserMachine",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "获取用户机器列表",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": UserMachineSchema,
    })
    def get(self, query: UserMachineSchema):
        return handler_get_user_machine(query)


class UserCaseCommit(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserCaseCommit",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "获取用户用例提交统计信息",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": UserCaseCommitSchema,
    })
    def get(self, query: UserCaseCommitSchema):
        return handler_get_user_case_commit(query)


class UserAssetRank(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_user_tag.__module__,
        "resource_name": "UserAssetRank",
        "func_name": "get",
        "tag": get_user_tag(),
        "summary": "ranked user列表",
        "externalDocs": {"description": "", "url": ""},
        "query_schema_model": PageBaseSchema,
    })
    def get(self, query: PageBaseSchema):
        return handler_get_user_asset_rank(query)


class UserPrivate(Resource):
    @auth.login_required()
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def get(self, user_id):
        return handler_private(user_id)
