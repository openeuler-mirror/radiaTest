from flask import jsonify, g, request, current_app
from sqlalchemy import or_, and_

from server import db
from server.model.administrator import Admin
from server.model.organization import Organization, ReUserOrganization, OrganizationRole
from server.model.group import Group, ReUserGroup, GroupRole
from server.model.user import User
from server.model.pmachine import Pmachine
from server.model.vmachine import Vmachine
from server.model.permission import ReScopeRole, ReUserRole, Role, Scope
from server.utils.permission_utils import PermissionItemsPool
from server.utils.response_util import RET
from server.utils.db import Insert, Delete, collect_sql_error
from server.utils.read_from_yaml import get_default_suffix


class RoleHandler:
    @staticmethod
    @collect_sql_error
    def get(role_id):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The role is not exist")

        return_data = role.to_json()

        scopes = []

        for re in role.re_scope_role:
            scope = Scope.query.filter_by(id=re.scope_id).first()
            scopes.append(scope.to_json())

        return_data.update({"scopes": scopes})

        users = []

        for re in role.re_user_role:
            user = User.query.filter_by(gitee_id=re.user_id).first()
            users.append(user.to_dict())

        return_data.update({"users": users})

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = []
        admin = Admin.query.filter_by(account=g.gitee_login).first()
        if not admin:
            _filter = [and_(ReUserRole.user_id == g.gitee_id,
                            Role.name == 'admin',
                            or_(
                                Role.type == 'group',
                                Role.type == 'org'
                                )
                            )
                       ]
            _roles = Role.query.join(ReUserRole).filter(*_filter).all()
            group_id = []
            org_id = []
            for _ in _roles:
                if _.type == 'group':
                    group_id.append(_.group_id)
                else:
                    org_id.append(_.org_id)
            filter_params.append(or_(Role.group_id.in_(group_id), Role.org_id.in_(org_id)))
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'name':
                filter_params.append(Role.name.like(f'%{value}%'))
            if key == 'description':
                filter_params.append(Role.description.like(f'%{value}%'))

        roles = Role.query.filter(*filter_params).all()
        return_data = [role.to_json() for role in roles]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__

        _relation = None
        _role = None
        if _body["type"] == "group":
            _relation = Group.query.filter_by(
                id=_body["group_id"]
            ).first()
            _role = Role.query.filter_by(
                name=_body["name"],
                group_id=_body["group_id"],
                type="group"
            ).first()
        if _body["type"] == "org":
            _relation = Organization.query.filter_by(
                id=_body["org_id"]
            ).first()
            _role = Role.query.filter_by(
                name=_body["name"],
                org_id=_body["org_id"],
                type="org"
            ).first()
        if _body["type"] == "public":
            _role = Role.query.filter_by(
                name=_body["name"],
                type="public"
            ).first()

        if _body["type"] == "person":
            _role = Role.query.filter_by(
                name=_body["name"],
                type="person"
            ).first()

        if not _relation and _body["type"] != "public":
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Group/Organization has not been exist")

        if _role is not None:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="This role is already exist")

        _ = Insert(Role, _body).insert_id(Role, '/role')

        role = Role.query.get(_body["role_id"])
        _origin = [_ for _ in role.children]
        role.children.append(Role.query.get(_))
        _after = [_ for _ in role.children]
        role.add_update(difference=list(set(_after) - set(_origin)))
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(role_id):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The role to delete is not exist")
        if role.necessary:
            return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg="The role is not allowed to delete")
        roles = [_.name for _ in role.children]
        if roles:
            return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg=f"The role is related to sub-role(s):{str(roles)}")
        _urs = ReUserRole.query.filter_by(role_id=role.id).all()
        _srs = ReScopeRole.query.filter_by(role_id=role.id).all()
        for _re in _urs:
            Delete(ReUserRole, {"id": _re.id}).single()
        for _re in _srs:
            Delete(ReScopeRole, {"id": _re.id}).single()
        role.delete()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(role_id, body):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The role to delete is not exist")

        role.name = body.name

        role.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def get_role(query):
        suffix = get_default_suffix(query.type)
        all_filter = [Role.type == query.type]
        if query.type != 'public':
            all_filter.append(Role.org_id == query.org_id)
            if query.type == 'group':
                all_filter.append(Role.group_id == query.group_id)

        _all = Role.query.filter(*all_filter).all()
        role_list = []
        for _role in _all:
            role_dict = _role.to_json()
            if _role.name == suffix:
                role_dict['default'] = True
            role_list.append(role_dict)
        return jsonify(error_code=RET.OK, error_msg="OK", data=role_list)


class ScopeHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = []
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'alias':
                filter_params.append(Scope.alias.like(f'%{value}%'))
            if key == 'uri':
                filter_params.append(Scope.uri.like(f'%{value}%'))
            if key == 'act':
                filter_params.append(Scope.act == value)
            if key == 'eft':
                filter_params.append(Scope.eft == value)

        scopes = Scope.query.filter(*filter_params).all()
        return_data = [scope.to_json() for scope in scopes]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def create(body):
        _ = Insert(Scope, body.__dict__).insert_id(Scope, '/scope')
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(role_id):
        scope = Scope.query.filter_by(id=role_id).first()
        if not scope:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The scope to delete is not exist")

        db.session.delete(scope)
        db.session.commit()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update(role_id, body):
        scope = Scope.query.filter_by(id=role_id).first()
        if not scope:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The scope to delete is not exist")

        scope.alias = body.alias
        scope.uri = body.uri
        scope.act = body.act
        scope.eft = body.eft

        scope.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")


class BindingHandler:
    @staticmethod
    @collect_sql_error
    def bind_scope_role(body):
        _scope = Scope.query.filter_by(id=body.scope_id).first()
        _role = Role.query.filter_by(id=body.role_id).first()

        if not _scope or not _role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Scope/Role has not been exist")

        return Insert(ReScopeRole, body.__dict__).single()

    @staticmethod
    @collect_sql_error
    def bind_user_role(body):
        _user = User.query.filter_by(gitee_id=body.user_id).first()
        _role = Role.query.filter_by(id=body.role_id).first()

        if not _user or not _role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="User/Role has not been exist")

        return Insert(ReUserRole, body.__dict__).single()


class RoleLimitedHandler:
    def __init__(self, _type='public', org_id=None, group_id=None, role_id=None):
        self.role_id = None

        _role = Role.query.filter_by(id=role_id).first()
        if _role and _role.type == _type and _role.group_id == group_id and (
                _type == 'public' or _type == 'group' or _type == 'org' and _role.org_id == org_id):
            self.role_id = _role.id


class UserRoleLimitedHandler(RoleLimitedHandler):
    def __init__(self, _type='public', org_id=None, group_id=None, body=None):
        super().__init__(_type, org_id, group_id, body.role_id)
        self.org_id = org_id
        self.group_id = group_id
        self.user_id = None
        _user = User.query.filter_by(gitee_id=body.user_id).first()
        if _user:
            self.user_id = _user.gitee_id

    def bind_user(self):
        if not self.role_id or not self.user_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="permission denied")

        _role = Role.query.get(self.role_id)

        if _role.type == 'group':
            rug = ReUserGroup.query.filter_by(group_id=self.group_id, user_gitee_id=self.user_id).first()
            if _role.name == 'admin':
                rug.role_type = GroupRole.admin.value
            else:
                rug.role_type = GroupRole.user.value
            rug.add_update()
        elif _role.type == 'org':
            ruo = ReUserOrganization.query.filter_by(organization_id=self.org_id,
                                                     user_gitee_id=self.user_id).first()
            if _role.name == 'admin':
                ruo.role_type = OrganizationRole.admin.value
            else:
                ruo.role_type = OrganizationRole.user.value
            ruo.add_update()

        return Insert(
            ReUserRole,
            {
                "user_id": self.user_id,
                "role_id": self.role_id
            }
        ).single()

    def unbind_user(self):
        if not self.role_id or not self.user_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="permission denied")

        re = ReUserRole.query.filter_by(role_id=self.role_id, user_id=self.user_id).first()
        if not re:
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="This Binding is already not exist")
        rug = ReUserGroup.query.filter_by(user_gitee_id=self.user_id, group_id=re.role.group_id).first()
        if re.role.name == 'admin' and rug.role_type == GroupRole.create_user.value:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="group creator user-role bind is not allowed to untie")
        return Delete(
            ReUserRole,
            {
                "id": re.id,
            }
        ).single()


class ScopeRoleLimitedHandler(RoleLimitedHandler):
    def __init__(self, _type='public', org_id=None, group_id=None, body=None):
        super().__init__(_type, org_id, group_id, body.role_id)
        self.scope_id = None
        _scope = Scope.query.filter_by(id=body.scope_id).first()
        if _scope:
            self.scope_id = _scope.id

    def bind_scope(self):
        if not self.role_id or not self.scope_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="permission denied")

        return Insert(
            ReScopeRole,
            {
                "scope_id": self.scope_id,
                "role_id": self.role_id
            }
        ).single()

    def unbind_scope(self):
        if not self.role_id or not self.scope_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="permission denied")

        re = ReScopeRole.query.filter_by(role_id=self.role_id, scope_id=self.scope_id).first()
        if not re:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="This Binding is already not exist")

        return Delete(
            ReScopeRole,
            {
                "id": re.id,
            }
        ).single()


class AccessableMachinesHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        namespace, origin_pool = None, []

        user = User.query.filter_by(gitee_id=g.gitee_id).first()

        if query.machine_type == "physical":
            namespace = "pmachine"
            if query.machine_purpose != "create_vmachine":
                origin_pool = Pmachine.query.filter(
                    Pmachine.machine_group_id==query.machine_group_id,
                    Pmachine.frame==query.frame,
                    Pmachine.state=="occupied",
                    Pmachine.locked==False,
                    Pmachine.status=="on",
                    or_(
                        Pmachine.description==current_app.config.get(
                            "CI_PURPOSE"
                        ),
                        and_(
                            Pmachine.occupier==user.gitee_name,
                            Pmachine.description!=current_app.config.get(
                                "CI_HOST"
                            )
                        )
                    ),
                ).all()
            else:
                origin_pool = Pmachine.query.filter(
                    Pmachine.machine_group_id==query.machine_group_id,
                    Pmachine.frame==query.frame,
                    Pmachine.state=="occupied",
                    Pmachine.locked==False,
                    Pmachine.status=="on",
                    Pmachine.description==current_app.config.get(
                        "CI_HOST"
                    ),
                ).all()

        elif query.machine_type == "kvm":
            namespace = "vmachine"
            origin_pool = Vmachine.query.join(Pmachine).filter(
                Pmachine.machine_group_id==query.machine_group_id,
                Vmachine.frame==query.frame,
                Vmachine.status=="running",
            ).all()

        if not namespace:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="unsupported machine type"
            )

        permission_pool = PermissionItemsPool(
            origin_pool,
            namespace,
            "GET",
            request.headers.get("authorization"),
        )

        allow_machines = permission_pool.allow_list

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=allow_machines
        )