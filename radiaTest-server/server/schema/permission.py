from typing import Optional
from pydantic import BaseModel, root_validator
from server.schema import Frame, MachinePurpose, MachineType, RoleType, ActionType, EffectType


class RoleBaseSchema(BaseModel):
    name: str
    type: RoleType = "public"
    description: Optional[str]
    group_id: Optional[int]
    org_id: Optional[int]

    @root_validator
    def validate_type(cls, values):
        if values.get("type") == "group" and (not values.get("group_id") or not values.get("org_id")):
            raise ValueError("Lack of org_id/group_id for a role of group")

        if values.get("type") == "org" and not values.get("org_id"):
            raise ValueError("Lack of org_id for a role of organization")
        
        return values


class RoleUpdateSchema(RoleBaseSchema):
    name: Optional[str]


class RoleQuerySchema(RoleBaseSchema):
    name: Optional[str]
    type: Optional[RoleType]
    group_id: Optional[int]
    org_id: Optional[int]


class UserRoleBaseSchema(BaseModel):
    user_id: int
    role_id: int


class ScopeRoleBaseSchema(BaseModel):
    scope_id: int
    role_id: int


class ScopeBaseSchema(BaseModel):
    alias: str
    uri: str
    act: ActionType
    eft: EffectType

class ScopeUpdateSchema(ScopeBaseSchema):
    alias: Optional[str]
    uri: Optional[str]
    act: Optional[ActionType]
    eft: Optional[EffectType]


class ScopeQuerySchema(ScopeUpdateSchema):
    pass


class AccessableMachinesQuery(BaseModel):
    machine_group_id: int
    machine_purpose: MachinePurpose
    machine_type: MachineType
    frame: Frame