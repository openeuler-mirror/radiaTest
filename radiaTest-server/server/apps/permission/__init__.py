from flask_restful import Api

from .routes import GroupScopeEvent, OrganizationScopeEvent, RoleEvent, ScopeRolePersonEvent
from .routes import RoleItemEvent
from .routes import AllRoleEvent
from .routes import ScopeEvent
from .routes import ScopeItemEvent
from .routes import UserRolePublicEvent
from .routes import UserRoleOrgEvent
from .routes import UserRoleGroupEvent
from .routes import ScopeRolePublicEvent
from .routes import ScopeRoleOrgEvent
from .routes import ScopeRoleGroupEvent
from .routes import AccessableMachinesEvent


def init_api(api: Api):
    api.add_resource(RoleEvent, "/api/v1/role")
    api.add_resource(RoleItemEvent, "/api/v1/role/<int:role_id>")
    api.add_resource(AllRoleEvent, "/api/v1/role/default")
    api.add_resource(ScopeEvent, "/api/v1/scope")
    api.add_resource(ScopeItemEvent, "/api/v1/scope/<int:scope_id>")
    api.add_resource(OrganizationScopeEvent, "/api/v1/scope/org/<int:org_id>")
    api.add_resource(GroupScopeEvent, "/api/v1/scope/group/<int:group_id>")
    api.add_resource(UserRolePublicEvent, "/api/v1/user-role")
    api.add_resource(UserRoleOrgEvent, "/api/v1/user-role/org/<int:org_id>")
    api.add_resource(UserRoleGroupEvent, "/api/v1/user-role/group/<int:group_id>")
    api.add_resource(ScopeRolePublicEvent, "/api/v1/scope-role")
    api.add_resource(ScopeRoleOrgEvent, "/api/v1/scope-role/org/<int:org_id>")
    api.add_resource(ScopeRoleGroupEvent, "/api/v1/scope-role/group/<int:group_id>")
    api.add_resource(ScopeRolePersonEvent, "/api/v1/scope-role/user/<int:gitee_id>")
    api.add_resource(AccessableMachinesEvent, "/api/v1/accessable-machines")
