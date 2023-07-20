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
from server.utils.cla_util import ClaSignSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.user import UserTaskSchema, UserMachineSchema
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

oauth = Blueprint('oauth', __name__)


@oauth.route("/api/v1/oauth/callback", methods=["GET"])
def oauth_callback():
    return handler_oauth_callback()


class OauthLogin(Resource):
    @validate()
    def get(self, query: OauthLoginSchema):
        return handler_oauth_login(query)


class Login(Resource):
    @validate()
    def get(self, query: LoginSchema):
        return handler_login_callback(query)


class User(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: UserQuerySchema):
        return handler_get_all(query)


class UserItem(Resource):
    @validate()
    def post(self, user_id, body: ClaSignSchema):
        return handler_register(user_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, user_id, body: UpdateUserSchema):
        return handler_update_user(user_id, body)

    @auth.login_required()
    @response_collect
    def get(self, user_id):
        return handler_user_info(user_id)


class Logout(Resource):
    @auth.login_required()
    @response_collect
    def delete(self):
        return handler_logout()


class Org(Resource):
    @auth.login_required()
    @response_collect
    def put(self, org_id):
        return handler_select_default_org(org_id)


class Group(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, group_id, body: JoinGroupSchema):
        return handler_add_group(group_id, body)


class UserTask(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: UserTaskSchema):
        return handler_get_user_task(query)


class UserMachine(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: UserMachineSchema):
        return handler_get_user_machine(query)


class UserCaseCommit(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: UserCaseCommitSchema):
        return handler_get_user_case_commit(query)


class UserAssetRank(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: PageBaseSchema):
        return handler_get_user_asset_rank(query)