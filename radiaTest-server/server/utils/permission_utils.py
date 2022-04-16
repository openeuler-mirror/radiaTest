from asyncio import DatagramTransport
import json, yaml
from paramiko import SSHException
import requests
from server.utils.response_util import RET
from flask import jsonify, current_app, g
from typing import List

from flask import current_app, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from sqlalchemy import or_, and_
from server import db, redis_client
from server.model.permission import ReScopeRole, Role, Scope
from server.utils.db import Insert, Precise, Like
from server.utils.redis_util import RedisKey
from server.model import ReUserGroup


class PermissionManager:
    def get_api_list(self, table_name, path, item_id):
        with open(path, 'r', encoding='utf-8') as f:
            result = yaml.load(f.read(), Loader=yaml.FullLoader)

        allow_list = []
        deny_list = []
        result = result.get(table_name)
        for scope in result:
            allow_list.append({
                "uri": scope["uri"] % int(item_id),
                "alias": scope["alias"] + "_" + str(item_id) + "_allow",
                "act": scope["act"],
                "eft": "allow"
            })
            deny_list.append({
                "uri": scope["uri"] % int(item_id),
                "alias": scope["alias"] + "_" + str(item_id) + "_deny",
                "act": scope["act"],
                "eft": "deny"
            })
        return allow_list, deny_list

    def insert_scope(self, scope_datas):
        scope_ids = []
        get_scope_ids = []
        for sdata in scope_datas:
            try:
                _scope = Scope.query.filter_by(alias=sdata['alias']).first()
                if not _scope:
                    scope_id = Insert(Scope, sdata).insert_id(Scope, '/scope')
                    scope_ids.append(scope_id)
                    if sdata["act"] == "get":
                        get_scope_ids.append(scope_id)
            except (IntegrityError, SQLAlchemyError) as e:
                current_app.logger.error(str(e))
                continue
        return scope_ids, get_scope_ids

    def generate(self, scope_datas_allow, scope_datas_deny, _data: dict):
        default_role_filter = []
        role_filter = []
        if _data["permission_type"] == "public":
            role_filter = [and_(
                Role.name == "admin",
                Role.type == "public",
            )]
            default_role_filter = [and_(
                Role.name == "default",
                Role.type == "public",
            )]
        elif _data["permission_type"] == "group":
            role_filter = [and_(
                Role.name == "admin",
                Role.type == "group",
                Role.group_id == int(_data["group_id"])
            )]
            default_role_filter = [and_(
                Role.name == "default",
                Role.type == "group",
                Role.group_id == int(_data["group_id"])
            )]
        elif _data["permission_type"] == "org":
            org_id = int(redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')) if redis_client.hget(
                RedisKey.user(g.gitee_id), 'current_org_id') else int(_data["org_id"])
            role_filter = [and_(
                Role.name == "admin",
                Role.type == "org",
                Role.org_id == org_id
            )]
            default_role_filter = [and_(
                Role.name == "default",
                Role.type == "org",
                Role.org_id == org_id
            )]
        scope_allow_ids, get_scope_allow_ids = self.insert_scope(scope_datas_allow)
        _, _ = self.insert_scope(scope_datas_deny)
        if _data["permission_type"] != "person":
            default_role = Role.query.filter(*default_role_filter).first()
            if not default_role:
                return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist")

            role = Role.query.filter(*role_filter).first()
            if not role:
                return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist")

            try:
                for _id in get_scope_allow_ids:
                    scope_role_data = {
                        "scope_id": _id,
                        "role_id": default_role.id
                    }
                    Insert(ReScopeRole, scope_role_data).insert_id()

            except (SQLAlchemyError, IntegrityError) as e:
                raise RuntimeError(str(e)) from e

            try:
                for _id in scope_allow_ids:
                    scope_role_data = {
                        "scope_id": _id,
                        "role_id": role.id
                    }
                    Insert(ReScopeRole, scope_role_data).insert_id()
            except (SQLAlchemyError, IntegrityError) as e:
                raise RuntimeError(str(e)) from e

        _role = Role.query.filter_by(name=str(g.gitee_id), type="person").first()
        if not _role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist")
        try:
            for _id in scope_allow_ids:
                scope_role_data_creator = {
                    "scope_id": _id,
                    "role_id": _role.id
                }
                Insert(ReScopeRole, scope_role_data_creator).insert_id()
        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e

    def clean(self, uri_part, item_ids: List[int]):
        try:
            for item_id in item_ids:
                filter_str = uri_part + str(item_id)
                filter_params = []
                filter_params.append(Scope.uri.like(f'%{filter_str}%'))
                scopes = Scope.query.filter(*filter_params).all()
                for scope in scopes:
                    db.session.delete(scope)
                    db.session.commit()

        except (SQLAlchemyError, IntegrityError) as e:
            raise RuntimeError(str(e)) from e


class GetAllByPermission:
    def __init__(self, _table) -> None:
        self._table = _table
        current_org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        self.filter_params = [
            or_(
                self._table.permission_type == "public",
                and_(
                    self._table.permission_type == "org",
                    self._table.org_id == int(current_org_id)
                ),
                and_(
                    self._table.permission_type == "person",
                    self._table.org_id == int(current_org_id),
                    self._table.creator_id == int(g.gitee_id)
                )
            )
        ]

        _re_user_groups = ReUserGroup.query.filter_by(
            user_gitee_id=int(g.gitee_id), org_id=int(current_org_id)
        ).all()
        if _re_user_groups:
            group_ids = [re_user_group.group_id for re_user_group in _re_user_groups]
            self.filter_params = [
                or_(
                    self._table.permission_type == "public",
                    and_(
                        self._table.permission_type == "org",
                        self._table.org_id == int(current_org_id)
                    ),
                    and_(
                        self._table.permission_type == "group",
                        self._table.org_id == int(current_org_id),
                        self._table.group_id.in_(group_ids)),
                    and_(
                        self._table.permission_type == "person",
                        self._table.org_id == int(current_org_id),
                        self._table.creator_id == int(g.gitee_id)
                    )

                )
            ]

    def get_filter(self):
        return self.filter_params

    def get(self):
        tdata = self._table.query.filter(*self.filter_params).all()
        data = []
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )

    def fuzz(self, _data):
        for key, value in _data.items():
            if hasattr(self._table, key) and value is not None and key not in ("permission_type", "group_id"):
                self.filter_params.append(getattr(self._table, key).like("%{}%".format(value)))
        tdata = self._table.query.filter(*self.filter_params).all()
        data = []
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )

    def precise(self, _data):
        for key, value in _data.items():
            if hasattr(self._table, key) and value is not None and key not in ("permission_type", "group_id"):
                self.filter_params.append(getattr(self._table, key) == value)
        tdata = self._table.query.filter(*self.filter_params).all()
        data = []
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )

    def MultiCondition(self, _data):
        for key, value in _data.items():
            if hasattr(self._table, key) and value is not None and key not in ("permission_type", "group_id"):
                if not isinstance(value, list):
                    value = [value]
                self.filter_params.append(getattr(self._table, key).in_(value))
        tdata = self._table.query.filter(*self.filter_params).all()
        data = []
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )


class PermissionItemsPool:
    def __init__(
            self, origin_pool, namespace, act, auth):
        self.origin_pool = origin_pool
        self._root_url = "api/{}/{}".format(
            current_app.config.get("OFFICIAL_API_VERSION"),
            namespace
        )
        self.act = act
        self.auth = auth

    def _get_items(self, eft):
        return_data = []
        for _item in self.origin_pool:
            try:
                _url = "{}/{}".format(self._root_url, _item.id)
                _resp = requests.request(
                    method=self.act,
                    url="{}://{}:{}/{}".format(
                        current_app.config.get("PROTOCOL"),
                        current_app.config.get("SERVER_IP"),
                        current_app.config.get("SERVER_PORT"),
                        _url
                    ),
                    headers={
                        'Content-Type': 'application/json;charset=utf8',
                        'Authorization': self.auth,
                    },
                )
                if _resp.status_code != 200:
                    raise RuntimeError(_resp.text)

                _output = None
                try:
                    _output = json.loads(_resp.text)
                except AttributeError:
                    try:
                        _output = _resp.json
                    except AttributeError as e:
                        raise RuntimeError(str(e))

                if (_output.get("error_code") != RET.UNAUTHORIZE_ERR) == (eft == "allow"):
                    return_data.append(_item.to_json())

            except (SSHException, RuntimeError) as e:
                current_app.logger.warn(str(e))
                continue

        return return_data

    @property
    def allow_list(self):
        return self._get_items("allow")

    @property
    def deny_list(self):
        return self._get_items("deny")
