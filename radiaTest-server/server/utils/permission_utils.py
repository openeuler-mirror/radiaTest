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

import re
from typing import List

from flask import current_app, jsonify, g
import yaml
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, and_

from server import db, redis_client
from server.model.permission import ReScopeRole, Role, Scope
from server.utils.db import Insert
from server.utils.redis_util import RedisKey
from server.model import ReUserGroup
from server.utils.response_util import RET


class PermissionManager:
    def __init__(self, creator_id=None, org_id=None):
        self._creator_id = creator_id if creator_id else g.user_id
        self._org_id = org_id if org_id else int(redis_client.hget(RedisKey.user(g.user_id), "current_org_id"))

    @staticmethod
    def unbind_scope_role(scope_data_allow, del_scope: bool = False, role_id=None):
        """
        :description: delete the relationship between scope data and role
        :param: scope_data_allow, scope data allowed
        :param: del_scope: bool = False, whether delete scope data
        :param: role_id, role id
        """
        _scopes = list()
        for scope in scope_data_allow:
            _scop = Scope.query.filter_by(
                uri=scope.get("uri"), eft=scope.get("eft"), act=scope.get("act")
            ).first()
            if _scop:
                _scopes.append(_scop)

        if role_id:
            for _scope in _scopes:
                _srs = ReScopeRole.query.filter_by(
                    scope_id=_scope.id, role_id=role_id
                ).first()
                if _srs:
                    db.session.delete(_srs)
        else:
            for _scope in _scopes:
                _srs = ReScopeRole.query.filter_by(scope_id=_scope.id).all()
                for _re in _srs:
                    db.session.delete(_re)

        if del_scope:
            for _scope in _scopes:
                db.session.delete(_scope)
        db.session.commit()

    @staticmethod
    def clean(uri_part, item_ids: List[int]):
        """
        :description: clean all the associated permission relationship of apis
        :param: uri_part: str, Part of API address information
        :param: item_ids: List[int], resource ids
        """
        try:
            for item_id in item_ids:
                filter_str = uri_part + str(item_id)
                filter_params = list()
                filter_params.append(Scope.uri.like(f"%{filter_str}%"))
                scopes = Scope.query.filter(*filter_params).all()
                for scope in scopes:
                    rescoperoles = ReScopeRole.query.filter_by(
                        scope_id=scope.id).all()
                    for rescoperole in rescoperoles:
                        db.session.delete(rescoperole)
                        db.session.commit()
                    db.session.delete(scope)
                    db.session.commit()

        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e

    @staticmethod
    def insert_scope(scope_datas):
        """
        :description:insert scope data to database table
        :return: scope_ids: list, scpoe data id
                get_scope_ids: list, scpoe data id whose act is get
        """
        scope_ids = []
        get_scope_ids = []
        for sdata in scope_datas:
            try:
                _scope = Scope.query.filter_by(alias=sdata["alias"]).first()
                if not _scope:
                    scope_id = Insert(Scope, sdata).insert_id(Scope, "/scope")
                    scope_ids.append(scope_id)
                    if sdata["act"] == "get":
                        get_scope_ids.append(scope_id)
                else:
                    scope_ids.append(_scope.id)
                    if sdata["act"] == "get":
                        get_scope_ids.append(_scope.id)
            except (IntegrityError, SQLAlchemyError) as e:
                current_app.logger.error(str(e))
                continue
        return scope_ids, get_scope_ids

    @staticmethod
    def get_api_list(table_name, path, item_id):
        """
        :description: get api list
        :param table_name: str, table name
        :param path: str, api info file path
        :param item_id: int,  resource id, which is used to combine complete api
        :return: allow_list: list, list of allowed apis
                deny_list: list, list of denied apis
        """
        with open(path, "r", encoding="utf-8") as f:
            result = yaml.safe_load(f.read())

        allow_list = []
        deny_list = []
        result = result.get(table_name)
        for scope in result:
            allow_list.append(
                {
                    "uri": scope["uri"].replace(
                        "{" + table_name + "_id}", str(item_id)
                    ),
                    "alias": scope["alias"] + "_" + str(item_id) + "_allow",
                    "act": scope["act"],
                    "eft": "allow",
                }
            )
            deny_list.append(
                {
                    "uri": scope["uri"].replace(
                        "{" + table_name + "_id}", str(item_id)
                    ),
                    "alias": scope["alias"] + "_" + str(item_id) + "_deny",
                    "act": scope["act"],
                    "eft": "deny",
                }
            )
        return allow_list, deny_list

    def generate(
        self, scope_datas_allow, scope_datas_deny, _data: dict, admin_only=False
    ):
        """
        :description: Generate the associated permission relationship between resources and users
        :param: scope_datas_allow: list, scope data allowed
        :param: scope_datas_deny: list, scope data denied
        :param: _data: dict, filter condtions, contain permission_type, creator_id
        :param: admin_only: bool=false, when value is true, then current user is admin
        :return: jsonify
        """
        default_role_filter = []
        role_filter = []
        if _data["permission_type"] == "public":
            role_filter = [
                and_(
                    Role.name == "admin",
                    Role.type == "public",
                )
            ]
            default_role_filter = [
                and_(
                    Role.name == "default",
                    Role.type == "public",
                )
            ]
        elif _data["permission_type"] == "group":
            role_filter = [
                and_(
                    Role.name == "admin",
                    Role.type == "group",
                    Role.group_id == int(_data["group_id"]),
                )
            ]
            default_role_filter = [
                and_(
                    Role.name == "default",
                    Role.type == "group",
                    Role.group_id == int(_data["group_id"]),
                )
            ]
        elif _data["permission_type"] == "org":
            if self._org_id:
                org_id = self._org_id
            else:
                org_id = _data.get("org_id")
            role_filter = [
                and_(Role.name == "admin", Role.type ==
                     "org", Role.org_id == org_id)
            ]
            default_role_filter = [
                and_(Role.name == "default", Role.type ==
                     "org", Role.org_id == org_id)
            ]
        scope_allow_ids, get_scope_allow_ids = self.insert_scope(
            scope_datas_allow)
        _, _ = self.insert_scope(scope_datas_deny)
        if _data["permission_type"] != "person":
            default_role = Role.query.filter(*default_role_filter).first()
            if not default_role:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist"
                )

            role = Role.query.filter(*role_filter).first()
            if not role:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist"
                )

            if not admin_only:
                try:
                    for _id in get_scope_allow_ids:
                        scope_role_data = {"scope_id": _id, "role_id": default_role.id}
                        rsr = ReScopeRole.query.filter_by(
                            scope_id=_id, role_id=default_role.id
                        ).first()
                        if not rsr:
                            Insert(ReScopeRole, scope_role_data).insert_id()

                except (SQLAlchemyError, IntegrityError) as e:
                    raise RuntimeError(str(e)) from e

            try:
                for _id in scope_allow_ids:
                    scope_role_data = {"scope_id": _id, "role_id": role.id}
                    rsr = ReScopeRole.query.filter_by(
                        scope_id=_id, role_id=role.id
                    ).first()
                    if not rsr:
                        Insert(ReScopeRole, scope_role_data).insert_id()
            except (SQLAlchemyError, IntegrityError) as e:
                raise RuntimeError(str(e)) from e
        creator_id = self._creator_id
        if _data.get("creator_id"):
            creator_id = _data.get("creator_id")

        _role = Role.query.filter_by(
            name=str(creator_id), type="person").first()
        if not _role:
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist"
            )
        try:
            for _id in scope_allow_ids:
                scope_role_data_creator = {"scope_id": _id, "role_id": _role.id}
                rsr = ReScopeRole.query.filter_by(
                    scope_id=_id, role_id=_role.id
                ).first()
                if not rsr:
                    Insert(ReScopeRole, scope_role_data_creator).insert_id()
        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e
        return jsonify(error_code=RET.OK, error_msg="OK.")

    def bind_scope_nouser(self, scope_datas_allow, scope_datas_deny, _data: dict):
        """
        :description: Generate the associated permission relationship between resources and role
        :param: scope_datas_allow: list, scope data allowed
        :param: scope_datas_deny: list, scope data denied
        :param: _data: dict, filter condtions, contain permission_type, creator_id
        :return: jsonify
        """
        role_filter = []
        if _data["permission_type"] == "public":
            role_filter = [
                and_(
                    Role.name == "admin",
                    Role.type == "public",
                )
            ]
        elif _data["permission_type"] == "group":
            role_filter = [
                and_(
                    Role.name == "admin",
                    Role.type == "group",
                    Role.group_id == int(_data["group_id"]),
                )
            ]
        elif _data["permission_type"] == "org":
            role_filter = [
                and_(
                    Role.name == "admin",
                    Role.type == "org",
                    Role.org_id == int(_data.get("org_id")),
                )
            ]

        role = Role.query.filter(*role_filter).first()
        if not role:
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist"
            )
        scope_allow_ids, _ = self.insert_scope(scope_datas_allow)
        _, _ = self.insert_scope(scope_datas_deny)
        try:
            for _id in scope_allow_ids:
                scope_role_data = {"scope_id": _id, "role_id": role.id}
                rsr = ReScopeRole.query.filter_by(
                    scope_id=_id, role_id=role.id).first()
                if not rsr:
                    Insert(ReScopeRole, scope_role_data).insert_id()
        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e
        return jsonify(error_code=RET.OK, error_msg="OK.")

    def bind_scope_user(self, scope_datas_allow, scope_datas_deny, user_id):
        """
        :description: Generate the associated permission relationship between resources and person user
        :param: scope_datas_allow: list, scope data allowed
        :param: scope_datas_deny: list, scope data denied
        :param: user_id: int, user's  id
        :return: jsonify
        """
        _role = Role.query.filter_by(name=str(user_id), type="person").first()
        if not _role:
            return jsonify(
                error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist"
            )
        scope_allow_ids, _ = self.insert_scope(scope_datas_allow)
        _, _ = self.insert_scope(scope_datas_deny)
        try:
            for _id in scope_allow_ids:
                scope_role_data_creator = {"scope_id": _id, "role_id": _role.id}
                rsr = ReScopeRole.query.filter_by(
                    scope_id=_id, role_id=_role.id
                ).first()
                if not rsr:
                    Insert(ReScopeRole, scope_role_data_creator).insert_id()
        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e
        return jsonify(error_code=RET.OK, error_msg="OK.")


class GetAllByPermission:

    PATTERN = r'^group_\d+$'

    def __init__(self, _table, workspace=None, org_id=None) -> None:
        self._table = _table
        if hasattr(g, "user_id"):
            self.current_org_id = redis_client.hget(
                RedisKey.user(g.user_id),
                "current_org_id"
            )
            self.re_user_groups = ReUserGroup.query.filter_by(
                user_id=g.user_id, org_id=int(self.current_org_id), user_add_group_flag=True
            ).all()
        else:
            if not org_id:
                raise RuntimeError(f"need org_id")
            self.current_org_id = org_id
            self.re_user_groups = []

        self.filter_params = self._get_filter_params(workspace)

    @property
    def _default_ws_filter_params(self):
        if self.re_user_groups:
            group_ids = [re_user_group.group_id for re_user_group in self.re_user_groups]
            return [
                or_(
                    self._table.permission_type == "public",
                    and_(
                        self._table.permission_type == "org",
                        self._table.org_id == int(self.current_org_id),
                    ),
                    and_(
                        self._table.permission_type == "group",
                        self._table.org_id == int(self.current_org_id),
                        self._table.group_id.in_(group_ids),
                    ),
                    and_(
                        self._table.permission_type == "person",
                        self._table.org_id == int(self.current_org_id),
                        self._table.creator_id == g.user_id,
                    ),
                )
            ]
        if hasattr(g, "user_id"):
            return [
                or_(
                    self._table.permission_type == "public",
                    and_(
                        self._table.permission_type == "org",
                        self._table.org_id == int(self.current_org_id),
                    ),
                    and_(
                        self._table.permission_type == "person",
                        self._table.org_id == int(self.current_org_id),
                        self._table.creator_id == g.user_id,
                    ),
                )
            ]
        else:
            return [
                or_(
                    self._table.permission_type == "public",
                    and_(
                        self._table.permission_type == "org",
                        self._table.org_id == int(self.current_org_id),
                    )
                )
            ]

    @property
    def _org_ws_filter_params(self):
        return [
            and_(
                self._table.permission_type == "org",
                self._table.org_id == int(self.current_org_id),
            ),
        ]

    @property
    def _group_ws_filter_params(self):
        return [
            and_(
                self._table.permission_type == "group",
                self._table.org_id == int(self.current_org_id),
                self._table.group_id == self.group_id,
            ),
        ]

    def get_filter(self):
        """
        :description: get filter condtion
        :return: filter condtion
        """
        return self.filter_params

    def set_filter(self, filter_condition):
        """
        :description: set filter condtion
        :param: filter_condition, filter condtion
        """
        return self.filter_params.append(filter_condition)

    def get_data(self, ords: list = None, _type: str = "json"):
        """
        :description: get data from database table
        :param ords: list, sorting condition
        :param _type: str = [query, json, data], the return value type
        :return: query | data | jsonify
        """
        _query = self._table.query.filter(*self.filter_params)
        if ords:
            for _ord in ords:
                _query = _query.order_by(_ord)
        if _type == "query":
            return _query
        tdata = _query.all()
        data = []
        if tdata:
            data = [dt.to_json() for dt in tdata]
        if _type == "data":
            return data
        return jsonify(error_code=RET.OK, error_msg="OK!", data=data)
    
    def fuzz(self, _data, ords: list = None, _type: str = "json"):
        """
        :description: get data from database table by fuzzy match
        :param _data: dict, fuzzy match condition
        :param ords: list, sorting condition
        :param _type: str = [query, json, data], the return value type
        :return: query | data | jsonify
        """
        for key, value in _data.items():
            if (
                hasattr(self._table, key)
                and value is not None
                and key not in ("permission_type", "group_id")
            ):
                self.filter_params.append(
                    getattr(self._table, key).like("%{}%".format(value))
                )
        return self.get_data(ords, _type)

    def precise(self, _data, ords: list = None, _type: str = "json"):
        """
        :description: get data from database table by percise match
        :param _data: dict, percise match condition
        :param ords: list, sorting condition
        :param _type: str = [query, json, data], the return value type
        :return: query | data | jsonify
        """
        for key, value in _data.items():
            if (
                hasattr(self._table, key)
                and value is not None
                and key not in ("permission_type", "group_id")
            ):
                self.filter_params.append(getattr(self._table, key) == value)
        return self.get_data(ords, _type)

    def multicondition(self, _data, ords: list = None, _type: str = "json"):
        """
        :description: get data from database table by mutil-condition match
        :param _data: dict, mutil-condition match condition
        :param ords: list, sorting condition
        :param _type: str = [query, json, data], the return value type
        :return: query | data | jsonify
        """
        for key, value in _data.items():
            if (
                hasattr(self._table, key)
                and value is not None
                and key not in ("permission_type", "group_id")
            ):
                if not isinstance(value, list):
                    value = [value]
                self.filter_params.append(getattr(self._table, key).in_(value))
        return self.get_data(ords, _type)

    def single(self, _data):
        """
        :description: get data from database table by unique condition match
        :param _data: dict,  unique condition match condition
        :return: data
        """
        for key, value in _data.items():
            if (
                hasattr(self._table, key)
                and value is not None
                and key not in ("permission_type", "group_id")
            ):
                self.filter_params.append(getattr(self._table, key) == value)
        tdata = self._table.query.filter(*self.filter_params).first()
        return tdata

    def _get_filter_params(self, workspace=None):
        if not workspace or workspace == "default":
            return self._default_ws_filter_params

        elif workspace == "org":
            return self._org_ws_filter_params

        elif not re.match(GetAllByPermission.PATTERN, workspace):
            raise ValueError(f"{workspace} is not in valid pattern")

        else:
            self.group_id = int(workspace.split('_')[1])
            _re_user_group = ReUserGroup.query.filter_by(
                user_id=g.user_id,
                group_id=self.group_id,
                org_id=int(self.current_org_id),
            ).first()
            if not _re_user_group:
                raise RuntimeError(f"unauthorized access")

            return self._group_ws_filter_params
