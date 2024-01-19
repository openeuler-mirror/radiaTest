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

from server import casbin_enforcer, swagger_adapt
from server.schema.organization import OrgQuerySchema
from server.utils.cla_util import ClaBaseSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *


def get_organization_tag():
    return {
        "name": "组织",
        "description": "组织相关接口",
    }


class Cla(Resource):
    @swagger_adapt.api_schema_model_map({
        "__module__": get_organization_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Cla",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_organization_tag(),  # 当前接口所对应的标签
        "summary": "获取组织cla证书列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self):
        return handler_show_org_cla_list()


class Org(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_organization_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Org",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_organization_tag(),  # 当前接口所对应的标签
        "summary": "分页查询组织信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": OrgQuerySchema
    })
    def get(self, query: OrgQuerySchema):
        return handler_get_all_org(query)


class OrgStatistic(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_organization_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "OrgStatistic",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_organization_tag(),  # 当前接口所对应的标签
        "summary": "当前组织下用户数、用户组数量统计",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, org_id: int):
        return handler_org_statistic(org_id)


class Group(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_organization_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Group",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_organization_tag(),  # 当前接口所对应的标签
        "summary": "分页获取当前组织下的所有用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求参数
        "query_schema_model": PageBaseSchema
    })
    def get(self, org_id, query: PageBaseSchema):
        return handler_org_group_page(org_id, query)
