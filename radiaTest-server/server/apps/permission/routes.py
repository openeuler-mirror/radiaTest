from flask_restful import Resource
from flask_pydantic import validate

from server import casbin_enforcer
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.permission import (
    AccessableMachinesQuery,
    RoleBaseSchema, 
    RoleUpdateSchema, 
    RoleQuerySchema,
    ScopeBaseSchema, 
    ScopeUpdateSchema,
    ScopeQuerySchema,
    UserRoleBaseSchema,
    ScopeRoleBaseSchema
)
from .handler import AccessableMachinesHandler, RoleHandler, ScopeHandler, UserRoleLimitedHandler, ScopeRoleLimitedHandler


class RoleEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def get(self, query: RoleQuerySchema):
        return RoleHandler.get_all(query)

    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, body: RoleBaseSchema):
        return RoleHandler.create(body)


class RoleItemEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def put(self, role_id, body: RoleUpdateSchema):
        return RoleHandler.update(role_id, body)
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    def delete(self, role_id):
        return RoleHandler.delete(role_id)

    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    def get(self, role_id):
        return RoleHandler.get(role_id)


class ScopeEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def get(self, query: ScopeQuerySchema):
        return ScopeHandler.get_all(query)

    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, body: ScopeBaseSchema):
        return ScopeHandler.create(body)


class ScopeItemEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def put(self, scope_id, body: ScopeUpdateSchema):
        return ScopeHandler.update(scope_id, body)
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    def delete(self, scope_id):
        return ScopeHandler.delete(scope_id)


class UserRolePublicEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            body=body
        ).bind_user()
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            body=body
        ).unbind_user()


class UserRoleOrgEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, org_id, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            type='org', 
            org_id=org_id, 
            body=body
        ).bind_user()
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, org_id, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            type='org', 
            org_id=org_id, 
            body=body
        ).unbind_user()


class UserRoleGroupEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, group_id, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            type='group', 
            group_id=group_id, 
            body=body
        ).bind_user()

    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, group_id, body: UserRoleBaseSchema):
        return  UserRoleLimitedHandler(
            type='group', 
            group_id=group_id, 
            body=body
        ).unbind_user()


class ScopeRolePublicEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            body=body
        ).bind_scope()
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            body=body
        ).unbind_scope()


class ScopeRoleOrgEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, org_id, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            type='org', 
            org_id=org_id, 
            body=body
        ).bind_scope()

    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, org_id, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            type='org', 
            org_id=org_id, 
            body=body
        ).unbind_scope()


class ScopeRoleGroupEvent(Resource):
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def post(self, group_id, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            type='group', 
            group_id=group_id, 
            body=body
        ).bind_scope()
    
    @auth.login_required
    # @casbin_enforcer.enforcer
    @response_collect
    @validate()
    def delete(self, group_id, body: ScopeRoleBaseSchema):
        return  ScopeRoleLimitedHandler(
            type='group', 
            group_id=group_id, 
            body=body
        ).unbind_scope()
    

class AccessableMachinesEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: AccessableMachinesQuery):
        return AccessableMachinesHandler.get_all(query)