from flask_pydantic import validate
from flask_restful import Resource
from server.utils.cla_util import ClaBaseSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *


class Cla(Resource):
    def get(self):
        return handler_show_org_cla_list()

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, org_id, body: ClaBaseSchema):
        return handler_org_cla(org_id, body)


class User(Resource):
    @auth.login_required()
    @response_collect
    def get(self, org_id):
        return handler_org_user_page(org_id)


class Group(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, org_id, query: PageBaseSchema):
        return handler_org_group_page(org_id, query)
