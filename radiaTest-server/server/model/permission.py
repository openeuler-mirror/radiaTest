from flask import g

from server import db, casbin_enforcer, redis_client
from server.model import BaseModel
from server.utils.redis_util import RedisKey


class Role(db.Model, BaseModel):
    __tablename__ = "role"

    name = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(16), nullable=False)
    description = db.Column(db.Text(), nullable=True)

    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    re_scope_role = db.relationship("ReScopeRole", backref="role") 
    re_user_role = db.relationship("ReUserRole", backref="role") 

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
            "org_id": self.org_id,
            "org_name": self.organization.name if self.organization else None,
        }


class Scope(db.Model, BaseModel):
    __tablename__ = "scope"

    alias = db.Column(db.String(64), nullable=False, unique=True)
    uri = db.Column(db.String(256), nullable=False)
    act = db.Column(db.String(16), nullable=False)
    eft = db.Column(db.String(16), nullable=False)

    re_scope_role = db.relationship("ReScopeRole", backref="scope") 

    def to_json(self):
        return {
            "id": self.id,
            "alias": self.alias,
            "uri": self.uri,
            "act": self.act,
            "eft": self.eft
        }


class ReScopeRole(db.Model, BaseModel):
    __tablename__ = "re_scope_role"

    scope_id = db.Column(db.Integer(), db.ForeignKey("scope.id"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"))

    def _get_subject(self):
        _sub = self.role.name
        if self.role.type == "group":
            return self.role.group.name + '_' + _sub
        if self.role.type == "org":
            return self.role.organization.name + '_' + _sub
        
        return _sub

    def _generate_policy(self):
        _sub = self._get_subject()
        _obj = self.scope.uri
        _act = self.scope.act.upper()
        _eft = self.scope.eft
        _dom = redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")

        return [_sub, _obj, _act, _eft, _dom]

    def add_update(self, table=None, namespace=None):
        super().add_update(table, namespace)
        casbin_enforcer.adapter.add_policy("p", "p", self._generate_policy())

    def add_flush_commit(self, table=None, namespace=None):
        id = super().add_update(table, namespace)
        casbin_enforcer.adapter.add_policy("p", "p", self._generate_policy())
        return id

    def delete(self, table, namespace):
        _policy = self._generate_policy()
        super().delete(table, namespace)
        casbin_enforcer.adapter.remove_policy("p", "p", _policy)


class ReUserRole(db.Model, BaseModel):
    __tablename__ = "re_user_role"

    user_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"))

    def _get_subject(self):
        _sub = self.role.name
        if self.role.type == "group":
            return self.role.group.name + '_' + _sub
        if self.role.type == "org":
            return self.role.organization.name + '_' + _sub
        
        return _sub

    def _generate_group(self):
        _sub = str(self.user_id)
        _role = self._get_subject()
        _dom = redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")

        return [_sub, _role, _dom]

    def add_update(self, table=None, namespace=None):
        super().add_update(table, namespace)
        casbin_enforcer.adapter.add_policy("g", "g", self._generate_group())
    
    def add_flush_commit(self, table=None, namespace=None):
        id = super().add_update(table, namespace)
        casbin_enforcer.adapter.add_policy("g", "g", self._generate_group())
        return id

    def delete(self, table, namespace):
        _policy = self._generate_group()
        super().delete(table, namespace)
        casbin_enforcer.adapter.remove_policy("g", "g", _policy)

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.gitee_name,
            "role_id": self.role_id,
            "role_name": self.role.name,
            "role_type": self.role.type,
            "role_group": self.role.group_id,
            "role_org": self.role.org_id,
        }