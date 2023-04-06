from server import db, casbin_enforcer
from server.model.base import CasbinRoleModel, BaseModel


role_family = db.Table(
    'role_family',
    db.Column('parent_id', db.Integer, db.ForeignKey(
        'role.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey(
        'role.id'), primary_key=True)
)


class Role(db.Model, CasbinRoleModel):
    __tablename__ = "role"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(16), nullable=False)
    description = db.Column(db.Text(), nullable=True)
    necessary = db.Column(db.Boolean, default=False, nullable=False)

    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    re_scope_role = db.relationship("ReScopeRole", cascade="all, delete, delete-orphan", backref="role")
    re_user_role = db.relationship("ReUserRole", cascade="all, delete, delete-orphan", backref="role")

    children = db.relationship(
        "Role",
        secondary=role_family,
        primaryjoin=(role_family.c.parent_id == id),
        secondaryjoin=(role_family.c.child_id == id),
        backref=db.backref('parent', lazy='dynamic'),
        lazy='dynamic',
        cascade="all, delete"
    )

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

    def _generate_groups(self):
        groups = []
        for child in self.children:
            _sub = super()._get_subject_(child.type, child.name)
            _role = self._get_subject_(self.type, self.name)
            groups.append([_sub, _role])

        return groups

    def _get_update(self, difference):
        groups = []
        for child in difference:
            _sub = super()._get_subject_(child.type, child.name)
            _role = self._get_subject_(self.type, self.name)
            groups.append([_sub, _role])

        return groups

    def add_update(self, table=None, namespace=None, broadcast=False, difference=None):
        super().add_update(table, namespace)
        if difference:
            _update = self._get_update(difference)
            for group in _update:
                casbin_enforcer.adapter.add_policy("g", "g", group)

    def delete(self, table=None, namespace=None, broadcast=False):
        for group in self._generate_groups():
            casbin_enforcer.adapter.remove_policy("g", "g", group)
        super().delete(table, namespace, broadcast)


class Scope(db.Model, BaseModel):
    __tablename__ = "scope"

    id = db.Column(db.Integer(), primary_key=True)
    alias = db.Column(db.String(64), nullable=False, unique=True)
    uri = db.Column(db.String(256), nullable=False)
    act = db.Column(db.String(16), nullable=False)
    eft = db.Column(db.String(16), nullable=False)

    re_scope_role = db.relationship("ReScopeRole", cascade="all, delete, delete-orphan", backref="scope")

    def to_json(self):
        return {
            "id": self.id,
            "alias": self.alias,
            "uri": self.uri,
            "act": self.act,
            "eft": self.eft
        }


class ReScopeRole(db.Model, CasbinRoleModel):
    __tablename__ = "re_scope_role"

    id = db.Column(db.Integer(), primary_key=True)
    scope_id = db.Column(db.Integer(), db.ForeignKey("scope.id"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"))

    def _generate_policy(self):
        _sub = self._get_subject(self.role.type, self.role.name)
        _obj = self.scope.uri
        _act = self.scope.act.upper()
        _eft = self.scope.eft
        _dom = self._get_dom(self.scope.uri)
        return [_sub, _obj, _act, _eft, _dom]

    def add_update(self, table=None, namespace=None, broadcast=False):
        super().add_update(table, namespace, broadcast)
        casbin_enforcer.adapter.add_policy("p", "p", self._generate_policy())

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        id = super().add_update(table, namespace, broadcast)
        casbin_enforcer.adapter.add_policy("p", "p", self._generate_policy())
        return id

    def delete(self, table, namespace, broadcast=False):
        _policy = self._generate_policy()
        super().delete(table, namespace, broadcast)
        casbin_enforcer.adapter.remove_policy("p", "p", _policy)

    def to_json(self):
        return {
            "id": self.id,
            "scope_id": self.scope_id,
            "role_id": self.role_id,
            "role_name": self.role.name,
            "role_type": self.role.type,
            "role_group": self.role.group_id,
            "role_org": self.role.org_id,
        }


class ReUserRole(db.Model, CasbinRoleModel):
    __tablename__ = "re_user_role"

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"))

    def _generate_group(self):
        _sub = str(self.user_id)
        _role = self._get_subject(self.role.type, self.role.name)

        return [_sub, _role]

    def add_update(self, table=None, namespace=None, broadcast=False):
        super().add_update(table, namespace, broadcast)
        casbin_enforcer.adapter.add_policy("g", "g", self._generate_group())

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        id = super().add_update(table, namespace, broadcast)
        casbin_enforcer.adapter.add_policy("g", "g", self._generate_group())
        return id

    def delete(self, table, namespace, broadcast=False):
        _policy = self._generate_group()
        super().delete(table, namespace, broadcast)
        casbin_enforcer.adapter.remove_policy("g", "g", _policy)

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.user_name,
            "role_id": self.role_id,
            "role_name": self.role.name,
            "role_type": self.role.type,
            "role_group": self.role.group_id,
            "role_org": self.role.org_id,
        }