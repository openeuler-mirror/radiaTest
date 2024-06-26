# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
# @Date    : 2023/01/11
# @License : Mulan PSL v2
#####################################

import yaml
from flask import jsonify, g
from sqlalchemy import or_, and_

from server import db, redis_client
from server.model.administrator import Admin
from server.model.organization import Organization
from server.model.group import Group, ReUserGroup, GroupRole
from server.model.user import User
from server.model.permission import ReScopeRole, ReUserRole, Role, Scope
from server.utils.response_util import RET
from server.utils.db import Insert, Delete, collect_sql_error
from server.utils.read_from_yaml import get_default_suffix
from server.utils.redis_util import RedisKey
from server.utils.page_util import PageUtil
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import get_api


class RoleHandler:
    @staticmethod
    @collect_sql_error
    def get(role_id, query):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"query role[{role_id}] is not exist")
        is_admin = True
        current_user = g.user_id
        if not current_user.startswith("admin_"):
            if role.type != "person":
                filter_params = [ReUserRole.user_id == current_user]
                if role.type == "public":
                    filter_params.extend([Role.type == role.type, Role.name == "admin"])
                elif role.type == "org":
                    filter_params.extend([Role.type == role.type, Role.name == "admin", Role.org_id == role.org_id])
                elif role.type == "group":
                    filter_params.extend(
                        [
                            Role.type == role.type,
                            Role.name == "admin",
                            Role.org_id == role.org_id,
                            Role.group_id == role.group_id
                        ]
                    )
                user_admin = ReUserRole.query.join(Role).filter(
                    *filter_params
                ).all()
                if not user_admin:
                    is_admin = False
            elif role.type == "person" and role.name != current_user:
                is_admin = False

        return_data = role.to_json()

        scope_ids = [re.scope_id for re in role.re_scope_role]
        filter_params = [Scope.id.in_(scope_ids)]
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

        _scopes = Scope.query.filter(*filter_params).all()
        scopes = [scope.to_json() for scope in _scopes]
        return_data.update({"scopes": scopes})

        users = []
        if is_admin:
            for re in role.re_user_role:
                user = User.query.filter_by(user_id=re.user_id).first()
                users.append(user.to_dict())

        return_data.update({"users": users})

        return jsonify(error_code=RET.OK, error_msg=f"query role[{role_id}] is success", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = []

        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            filter_params = [
                or_(
                    and_(
                        ReUserGroup.org_id == redis_client.hget(RedisKey.user(g.user_id), 'current_org_id'),
                        ReUserGroup.user_id == g.user_id,
                        ReUserGroup.user_add_group_flag == True,
                        ReUserGroup.is_delete == False,
                    ),
                    Role.type == 'public',
                )
            ]
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'name':
                filter_params.append(Role.name.like(f'%{value}%'))
            if key == 'description':
                filter_params.append(Role.description.like(f'%{value}%'))

        roles = Role.query.outerjoin(
            ReUserGroup, Role.group_id == ReUserGroup.group_id
        ).filter(*filter_params).all()

        return_data = [role.to_json() for role in roles]

        return jsonify(error_code=RET.OK, error_msg="get role info success", data=return_data)

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
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="create role[{},{}] failed due to group/organization has not been exist".format(
                    _body.get("type"),
                    _body.get("name")
                )
            )

        if _role is not None:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="This role[{},{}] is already exist".format(_body.get("type"), _body.get("name"))
            )

        role_id = Insert(Role, _body).insert_id(Role, '/role')

        if _body.get("role_id"):
            role = Role.query.get(_body["role_id"])
            _origin = [_ for _ in role.children]
            role.children.append(Role.query.get(role_id))
            _after = [_ for _ in role.children]
            role.add_update(difference=list(set(_after) - set(_origin)))

        _data = {
            "permission_type": _body.get("type"),
            "org_id": _body.get("org_id"),
            "group_id": _body.get("group_id")
        }
        scope_data_allow, scope_data_deny = get_api("permission", "role.yaml", "role", role_id)
        PermissionManager().generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data
        )
        return jsonify(
            error_code=RET.OK,
            error_msg="create role[{},{}] success".format(_body.get("type"), _body.get("name"))
        )

    @staticmethod
    @collect_sql_error
    def delete(role_id):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"The role[{role_id}] to delete is not exist")
        if role.necessary:
            return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg=f"The role[{role_id}] is not allowed to delete")
        roles = [_.name for _ in role.children]
        if roles:
            return jsonify(
                error_code=RET.OTHER_REQ_ERR,
                error_msg=f"The role[{role_id}] is related to sub-role(s):{str(roles)}"
            )
        _urs = ReUserRole.query.filter_by(role_id=role.id).all()
        _srs = ReScopeRole.query.filter_by(role_id=role.id).all()
        for _re in _urs:
            Delete(ReUserRole, {"id": _re.id}).single()
        for _re in _srs:
            Delete(ReScopeRole, {"id": _re.id}).single()
        role.delete()
        return jsonify(error_code=RET.OK, error_msg=f"delete role[{role_id}] is success")

    @staticmethod
    @collect_sql_error
    def update(role_id, body):
        role = Role.query.filter_by(id=role_id).first()
        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"update role[{role_id}] is not exist")

        role.name = body.name

        role.add_update()

        return jsonify(error_code=RET.OK, error_msg=f"update role[{role_id}] success")

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
        return jsonify(error_code=RET.OK, error_msg="get role info success", data=role_list)


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

        scopes = Scope.query.filter(*filter_params)

        resp = PageUtil.get_data(scopes, query)
        result = resp.get_json()
        if result.get("error_code") != RET.OK:
            error_msg = result.get("error_msg")
            return jsonify(
                error_code=result.get("error_code"),
                error_msg=f"get scope failed for the reson[{error_msg}]"
            )
        else:
            return jsonify(
                error_code=RET.OK,
                error_msg="get scope info success",
                data=result.get("data")
            )

    @staticmethod
    def get_scopes_by_role(role_id, query):
        _re_scope_roles = ReScopeRole.query.filter_by(role_id=role_id).all()
        _re_scope_roles_id_list = [_re.id for _re in _re_scope_roles]

        _filter_params = [Scope.id.in_(_re_scope_roles_id_list)]
        if query.alias:
            _filter_params.append(Scope.alias.like(f'%{query.alias}%'))
        if query.uri:
            _filter_params.append(Scope.uri.like(f'%{query.uri}%'))
        if query.act:
            _filter_params.append(Scope.act == query.act)
        if query.eft:
            _filter_params.append(Scope.eft == query.eft)

        scopes = Scope.query.filter(*_filter_params).order_by(
            Scope.create_time.desc(),
            Scope.id.asc()
        )
        resp = PageUtil.get_data(scopes, query)
        result = resp.get_json()
        if result.get("error_code") != RET.OK:
            error_msg = result.get("error_msg")
            return jsonify(
                error_code=result.get("error_code"),
                error_msg=f"failed to obtain permission scope for role due to[{error_msg}]"
            )
        else:
            return jsonify(
                error_code=RET.OK,
                error_msg="success to obtain permission scope for role",
                data=result.get("data")
            )

    @staticmethod
    @collect_sql_error
    def get_public_all(query):
        with open('server/config/role_init.yaml', 'r', encoding='utf-8') as f:
            _role_infos = yaml.safe_load(f.read())
        _role_name = _role_infos.get('public').get("administrator")
        _filter_params = [
            Role.name == _role_name,
            Role.type == 'public',
        ]
        _role = Role.query.filter(*_filter_params).first()
        if not _role:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the administrator role of public does not exist"
            )
        return ScopeHandler.get_scopes_by_role(_role.id, query)

    @staticmethod
    @collect_sql_error
    def get_permitted_all(_type, table, owner_id, query):
        _owner = table.query.filter_by(id=owner_id).first()
        if not _owner:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"get {_type} scope failed due to the {_type}[{owner_id}] does not exist"
            )

        with open('server/config/role_init.yaml', 'r', encoding='utf-8') as f:
            _role_infos = yaml.safe_load(f.read())
        _role_name = _role_infos.get(_type).get("administrator")

        _filter_params = [
            Role.name == _role_name,
            Role.type == _type,
        ]
        if _type == "group":
            _filter_params.append(Role.group_id == owner_id)
        elif _type == "org":
            _filter_params.append(Role.org_id == owner_id)
        _role = Role.query.filter(*_filter_params).first()
        if not _role:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"get {_type} scope failed due to "
                          f"the administrator role of this {_type}[{owner_id}] does not exist"
            )
        return ScopeHandler.get_scopes_by_role(_role.id, query)

    @staticmethod
    @collect_sql_error
    def create(body):
        _ = Insert(Scope, body.__dict__).insert_id(Scope, '/scope')
        return jsonify(error_code=RET.OK, error_msg=f"scope[{body.alias, body.uri, body.act, body.eft}] add success")

    @staticmethod
    @collect_sql_error
    def delete(scope_id):
        scope = Scope.query.filter_by(id=scope_id).first()
        if not scope:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"delete scope[{scope_id}] is not exist")

        db.session.delete(scope)
        db.session.commit()

        return jsonify(error_code=RET.OK, error_msg=f"delete scope[{scope_id}] is success")

    @staticmethod
    @collect_sql_error
    def update(scope_id, body):
        scope = Scope.query.filter_by(id=scope_id).first()
        if not scope:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"update scope[{scope_id}] is not exist")

        scope.alias = body.alias
        scope.uri = body.uri
        scope.act = body.act
        scope.eft = body.eft

        scope.add_update()

        return jsonify(error_code=RET.OK, error_msg=f"update scope[{scope_id}] is success")


class RoleLimitedHandler:
    def __init__(self, _type='public', org_id=None, group_id=None, role_id=None):
        self.role_id = None

        _role = Role.query.filter_by(id=role_id).first()
        if _role and _role.type == _type:
            is_valid_role = (
                    (_type == 'group' and _role.group_id == group_id)
                    or (_type == 'org' and _role.org_id == org_id)
                    or _type == 'public' or _type == 'person'
            )
            if is_valid_role:
                self.role_id = _role.id


class UserRoleLimitedHandler(RoleLimitedHandler):
    def __init__(self, _type='public', org_id=None, group_id=None, body=None):
        super().__init__(_type, org_id, group_id, body.role_id)
        self.org_id = org_id
        self.group_id = group_id
        self.user_id = None
        _user = User.query.filter_by(user_id=body.user_id).first()
        if _user:
            self.user_id = _user.user_id

    def bind_user(self):
        if not self.role_id or not self.user_id:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="bind user and role failed due to empty role id or user id"
            )

        _role = Role.query.get(self.role_id)

        if _role.type == 'group':
            rug = ReUserGroup.query.filter_by(group_id=self.group_id, user_id=self.user_id).first()
            if _role.name == 'admin':
                rug.role_type = GroupRole.admin.value
            else:
                rug.role_type = GroupRole.user.value
            rug.add_update()

        Insert(
            ReUserRole,
            {
                "user_id": self.user_id,
                "role_id": self.role_id
            }
        ).single()
        return jsonify(error_code=RET.OK, error_msg=f"bind user[{self.user_id}] and role[{self.role_id}] is success")

    def unbind_user(self):
        if not self.role_id or not self.user_id:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="unbind user and role failed due to empty role id or user id"
            )

        re = ReUserRole.query.filter_by(role_id=self.role_id, user_id=self.user_id).first()
        if not re:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg=f"unbind user[{self.user_id}] and role[{self.role_id}] "
                          f"failed due to This Binding is already not exist"
            )
        if re.role.type == 'group':
            rug = ReUserGroup.query.filter_by(user_id=self.user_id, group_id=re.role.group_id).first()
            if not rug:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg=f"unbind user[{self.user_id}] and role[{self.role_id}] "
                              f"failed due to user-group binding not exist"
                )
            if re.role.name == 'admin' and rug.role_type == GroupRole.create_user.value:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg=f"unbind user[{self.user_id}] and role[{self.role_id}] "
                              f"failed due to group creator user-role bind is not allowed to untie"
                )

        Delete(
            ReUserRole,
            {
                "id": re.id,
            }
        ).single()
        return jsonify(
            error_code=RET.OK,
            error_msg=f"unbind user[{self.user_id}] and role[{self.role_id}] relation success"
        )


class ScopeRoleLimitedHandler(RoleLimitedHandler):
    def __init__(self, _type='public', org_id=None, group_id=None, body=None):
        super().__init__(_type, org_id, group_id, body.role_id)
        self.scope_id = None
        _scope = Scope.query.filter_by(id=body.scope_id).first()
        if _scope:
            self.scope_id = _scope.id

    def bind_scope(self):
        if not self.role_id or not self.scope_id:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="bind scope and role failed due to empty role id or scope id"
            )

        Insert(
            ReScopeRole,
            {
                "scope_id": self.scope_id,
                "role_id": self.role_id
            }
        ).single()
        return jsonify(error_code=RET.OK, error_msg=f"bind scope[{self.scope_id}] and role[{self.role_id}] is success")

    def unbind_scope(self):
        if not self.role_id or not self.scope_id:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="unbind scope and role failed due to empty scope id or role id"
            )

        re = ReScopeRole.query.filter_by(role_id=self.role_id, scope_id=self.scope_id).first()
        if not re:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"unbind scope[{self.role_id}] and role[{self.role_id}] "
                          f"failed due to this binding is already not exist"
            )

        Delete(
            ReScopeRole,
            {
                "id": re.id,
            }
        ).single()
        return jsonify(
            error_code=RET.OK,
            error_msg=f"unbind scope[{self.scope_id}] and role[{self.role_id}] success"
        )
