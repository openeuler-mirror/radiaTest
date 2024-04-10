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

from server import casbin_enforcer, swagger_adapt
from flask_restful import Resource
from flask_pydantic import validate

from server.apps.group.handlers import (
    handler_add_group,
    handler_update_group,
    handler_delete_group,
    handler_group_page,
    handler_group_user_page,
    handler_add_user,
    handler_update_user,
    handler_apply_join_group,
)
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.base import PageBaseSchema
from server.schema.group import (
    AddGroupUserSchema, 
    UpdateGroupUserSchema, 
    QueryGroupUserSchema,
)


def get_group_tag():
    return {
        "name": "用户组",
        "description": "用户组相关接口",
    }


class Group(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "Group",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "创建用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "application/json":
                    {"schema": {
                        "properties": {
                            "name": {
                                "title": "组名",
                                "type": "string"
                            },
                            "description": {
                                "title": "描述信息",
                                "type": "string"
                            }
                        },
                        "required": ["name"],
                        "title": "Group Schema",
                        "type": "object"
                    }}
            },
            "required": True
        }
    })
    def post(self):
        """
        创建一个用户组
        :return:
        """
        return handler_add_group()

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "Group",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "编辑用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "application/json":
                    {"schema": {
                        "properties": {
                            "name": {
                                "title": "组名",
                                "type": "string"
                            },
                            "description": {
                                "title": "描述信息",
                                "type": "string"
                            },
                            "avatar": {
                                "title": "图标",
                                "type": "string",
                                "format": "binary"
                            }
                        },
                        "required": ["name", "description"],
                        "title": "Group Schema",
                        "type": "object"
                    }}
            },
            "required": True
        }
    })
    def put(self, group_id):
        """
        编辑用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_update_group(group_id)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "Group",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "退出/删除用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, group_id):
        """
        退出/删除用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_delete_group(group_id)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "Group",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "获取当前用户所属的用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": [{
            "name": "page_num",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "页码",
            "schema": {"type": "integer"}},
            {
                "name": "page_size",
                "in": "query",
                "required": False,
                "style": "form",
                "explode": True,
                "description": "页大小",
                "schema": {"type": "integer"}},
            {
                "name": "name",
                "in": "query",
                "required": False,
                "style": "form",
                "explode": True,
                "description": "组名关键字",
                "schema": {"type": "string"}}


        ],
    })
    def get(self):
        """
        获取当前用户所属的用户组
        :return:
        """
        return handler_group_page()


class User(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "User",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "获取某一用户组下的所有用户",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryGroupUserSchema
    })
    def get(self, group_id, query: QueryGroupUserSchema):
        """
        获取某一用户组下的所有用户
        :param group_id: 用户组ID
        :param query: 查询参数
        :return:
        """
        return handler_group_user_page(group_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "User",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "添加用户组成员",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddGroupUserSchema
    })
    def post(self, group_id, body: AddGroupUserSchema):
        """
        添加用户组成员
        :param group_id: 用户组ID
        :param body:
        :return:
        """
        return handler_add_user(group_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "User",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "编辑用户组的用户状态",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UpdateGroupUserSchema
    })
    def put(self, group_id, body: UpdateGroupUserSchema):
        """
        编辑用户组的用户状态
        :param group_id: 用户组ID
        :param body:
        :return:
        """
        return handler_update_user(group_id, body)


class UserApplyGroup(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_group_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "UserApplyGroup",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_group_tag(),  # 当前接口所对应的标签
        "summary": "申请加入用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, group_id):
        """
        申请加入用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_apply_join_group(group_id)

