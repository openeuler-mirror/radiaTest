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

from flask_pydantic import validate
from flask_restful import Resource

from server import casbin_enforcer
from server.schema.organization import OrgQuerySchema
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


class Org(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: OrgQuerySchema):
        return handler_get_all_org(query)


class OrgStatistic(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, org_id: int):
        return handler_org_statistic(org_id)


class User(Resource):
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def get(self, org_id):
        return handler_org_user_page(org_id)


class Group(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, org_id, query: PageBaseSchema):
        return handler_org_group_page(org_id, query)
