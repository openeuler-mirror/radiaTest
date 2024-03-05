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

from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer, swagger_adapt
from server.model.organization import Organization
from server.model.group import Group
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.permission import (
    RoleBaseSchema,
    RoleUpdateSchema,
    RoleQuerySchema,
    ScopeBaseSchema,
    ScopeUpdateSchema,
    ScopeQuerySchema,
    UserRoleBaseSchema,
    ScopeRoleBaseSchema,
    AllRoleQuerySchema
)
from .handler import RoleHandler, ScopeHandler, UserRoleLimitedHandler, \
    ScopeRoleLimitedHandler


def get_permission_tag():
    return {
        "name": "权限",
        "description": "权限相关接口",
    }


class RoleEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RoleEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "角色查询",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": RoleQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: RoleQuerySchema):
        return RoleHandler.get_all(query)

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RoleEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "角色创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RoleQuerySchema
    })
    def post(self, body: RoleBaseSchema):
        return RoleHandler.create(body)


class RoleItemEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RoleItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "编辑角色",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RoleUpdateSchema
    })
    def put(self, role_id, body: RoleUpdateSchema):
        return RoleHandler.update(role_id, body)

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RoleItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "删除角色",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, role_id):
        return RoleHandler.delete(role_id)

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RoleItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "获取当前角色下所有用户、所有权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeQuerySchema
    })
    def get(self, role_id, query: ScopeQuerySchema):
        return RoleHandler.get(role_id, query)


class AllRoleEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "AllRoleEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "获取角色列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": AllRoleQuerySchema
    })
    def get(self, query: AllRoleQuerySchema):
        return RoleHandler.get_role(query)


class ScopeEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "分页查询权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeQuerySchema
    })
    def get(self, query: ScopeQuerySchema):
        return ScopeHandler.get_all(query)

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "创建权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeBaseSchema
    })
    def post(self, body: ScopeBaseSchema):
        return ScopeHandler.create(body)


class ScopeItemEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "更新权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeUpdateSchema
    })
    def put(self, scope_id, body: ScopeUpdateSchema):
        return ScopeHandler.update(scope_id, body)

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "删除权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, scope_id):
        return ScopeHandler.delete(scope_id)


class PublicScopeEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PublicScopeEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "分页查询public下所有权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeQuerySchema
    })
    def get(self, query: ScopeQuerySchema):
        return ScopeHandler.get_public_all(
            query=query,
        )


class OrganizationScopeEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "OrganizationScopeEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "分页查询当前组织下所有允许权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeQuerySchema
    })
    def get(self, org_id, query: ScopeQuerySchema):
        return ScopeHandler.get_permitted_all(
            _type="org",
            table=Organization,
            owner_id=org_id,
            query=query,
        )


class GroupScopeEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "GroupScopeEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "分页查询当前用户组下所有允许权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeQuerySchema
    })
    def get(self, group_id, query: ScopeQuerySchema):
        return ScopeHandler.get_permitted_all(
            _type="group",
            table=Group,
            owner_id=group_id,
            query=query,
        )


class UserRolePublicEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRolePublicEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "Public用户绑定角色",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UserRoleBaseSchema
    })
    def post(self, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            body=body
        ).bind_user()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRolePublicEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "Public用户解除角色绑定",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": UserRoleBaseSchema
    })
    def delete(self, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            body=body
        ).unbind_user()


class UserRoleOrgEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRoleOrgEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "组织用户绑定角色",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UserRoleBaseSchema
    })
    def post(self, org_id, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            _type='org',
            org_id=org_id,
            body=body
        ).bind_user()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRoleOrgEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "组织用户解除角色绑定",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": UserRoleBaseSchema
    })
    def delete(self, org_id, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            _type='org',
            org_id=org_id,
            body=body
        ).unbind_user()


class UserRoleGroupEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRoleGroupEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "用户组用户绑定角色",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": UserRoleBaseSchema
    })
    def post(self, group_id, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            _type='group',
            group_id=group_id,
            body=body
        ).bind_user()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UserRoleGroupEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "用户组用户解除角色绑定",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": UserRoleBaseSchema
    })
    def delete(self, group_id, body: UserRoleBaseSchema):
        return UserRoleLimitedHandler(
            _type='group',
            group_id=group_id,
            body=body
        ).unbind_user()


class ScopeRolePublicEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRolePublicEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "Public角色绑定权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeRoleBaseSchema
    })
    def post(self, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            body=body
        ).bind_scope()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRolePublicEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "Public角色删除权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeRoleBaseSchema
    })
    def delete(self, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            body=body
        ).unbind_scope()


class ScopeRoleOrgEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRoleOrgEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "组织角色绑定权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeRoleBaseSchema
    })
    def post(self, org_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='org',
            org_id=org_id,
            body=body
        ).bind_scope()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRoleOrgEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "组织角色删除权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeRoleBaseSchema
    })
    def delete(self, org_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='org',
            org_id=org_id,
            body=body
        ).unbind_scope()


class ScopeRoleGroupEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRoleGroupEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "用户组角色绑定权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeRoleBaseSchema
    })
    def post(self, group_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='group',
            group_id=group_id,
            body=body
        ).bind_scope()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRoleGroupEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "用户组角色删除权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeRoleBaseSchema
    })
    def delete(self, group_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='group',
            group_id=group_id,
            body=body
        ).unbind_scope()


class ScopeRolePersonEvent(Resource):
    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRolePersonEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "个人绑定权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ScopeRoleBaseSchema
    })
    def post(self, user_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='person',
            body=body
        ).bind_scope()

    @auth.login_required
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_permission_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ScopeRolePersonEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_permission_tag(),  # 当前接口所对应的标签
        "summary": "个人删除权限域",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ScopeRoleBaseSchema
    })
    def delete(self, user_id, body: ScopeRoleBaseSchema):
        return ScopeRoleLimitedHandler(
            _type='person',
            body=body
        ).unbind_scope()
