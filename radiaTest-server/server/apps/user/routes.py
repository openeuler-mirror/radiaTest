from flask import Blueprint
from flask_restful import Resource
from flask_pydantic import validate
from server.utils.db import Select
from server.utils.cla_util import ClaSignSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.user import UpdateUserSchema, JoinGroupSchema, UserQuerySchema, UserTaskSchema, UserMachineSchema
from .handlers import handler_gitee_callback
from .handlers import handler_gitee_login
from .handlers import handler_register
from .handlers import handler_update_user
from .handlers import handler_user_info
from .handlers import handler_logout
from .handlers import handler_select_default_org
from .handlers import handler_add_group
from .handlers import handler_get_all
from .handlers import handler_get_user_task
from .handlers import handler_get_user_machine

gitee = Blueprint('gitee', __name__)


@gitee.route("/api/v1/gitee/oauth/callback", methods=["GET"])
def gitee_callback():
    return handler_gitee_callback()


class GiteeLogin(Resource):
    def get(self):
        return handler_gitee_login()


class User(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: UserQuerySchema):
        return handler_get_all(query)


class UserItem(Resource):
    @validate()
    def post(self, gitee_id, body: ClaSignSchema):
        return handler_register(gitee_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, gitee_id, body: UpdateUserSchema):
        return handler_update_user(gitee_id, body)

    @auth.login_required()
    @response_collect
    def get(self, gitee_id):
        return handler_user_info(gitee_id)


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

# class Token(Resource):
#     @validate()
#     def put(self, body: RefreshTokenSchema):
#         return handler_token(body.refresh_token)


class UserTask(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: UserTaskSchema):
        return handler_get_user_task(body)


class UserMachine(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: UserMachineSchema):
        return handler_get_user_machine(body)