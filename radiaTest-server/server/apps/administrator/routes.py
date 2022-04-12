from flask_restful import Resource
from flask_pydantic import validate
from server.schema.administrator import LoginSchema, RegisterSchema
from server.schema.organization import AddSchema, UpdateSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *


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
    def get(self):
        return handler_read_org_list()

    @auth.login_required()
    @response_collect
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
    @validate()
    def put(self, org_id, body: UpdateSchema):
        return handler_update_org(org_id, body)
