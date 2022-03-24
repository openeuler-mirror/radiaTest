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
    def get_api_list(self, path, item_id):
        with open(path, 'r', encoding='utf-8') as f:
            result = yaml.load(f.read(), Loader=yaml.FullLoader)

        allow_list = []
        deny_list = []
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
        for sdata in scope_datas:
            try:
                scope_id = Insert(Scope, sdata).insert_id(Scope, '/scope')
                scope_ids.append(scope_id)
            except (IntegrityError, SQLAlchemyError) as e:
                current_app.logger.error(str(e))
                continue
        return scope_ids

    def generate(self, scope_datas_allow, scope_datas_deny, permission_type, group_id = None):
        if permission_type == "public": role_name = "public_admin"
        elif permission_type == "person": role_name = permission_type + "_" + str(g.gitee_id)
        elif permission_type == "group": role_name = permission_type + "_" + str(group_id) + "_admin"
        elif permission_type == "org": role_name = permission_type + "_" + redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id') + "_admin"
        role = Precise(
            Role,
            {
                "name": role_name,
                "type": permission_type
            },
        ).first()

        if not role:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Role has not been exist")
    
        scope_allow_ids = self.insert_scope(scope_datas_allow)
        _ = self.insert_scope(scope_datas_deny)

        try:
            for _id in scope_allow_ids:
                scope_role_data = {
                    "scope_id": _id,
                    "role_id": role.id
                }
                Insert(ReScopeRole, scope_role_data).insert_id()

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
        data=[]
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )
    
    def fuzz(self, _data):
        for key, value in _data.items() and key not in ("permission_type","group_id"):
            if hasattr(self._table, key):
                self.filter_params.append(getattr(self._table, key).like("%{}%".format(value)))
        tdata = self._table.query.filter(*self.filter_params).all()
        data=[]
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )

    def precise(self, _data):
        for key, value in _data.items() and key not in ("permission_type","group_id"):
            if hasattr(self._table, key):
                self.filter_params.append(getattr(self._table, key) == value)
        tdata = self._table.query.filter(*self.filter_params).all()
        data=[]
        if tdata:
            data = [dt.to_json() for dt in tdata]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK!",
            data=data
        )


class PermissionItemsPool:
    def __init__(
        self, origin_pool, namespace, act, auth, get_query_object=False
    ):
        self.origin_pool = origin_pool
        self._root_url = "api/{}/{}".format(
            current_app.config.get("OFFICIAL_API_VERSION"), 
            namespace
        )
        self.act = act
        self.auth = auth
        self.get_query_object = get_query_object

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
                    if not self.get_query_object:
                        return_data.append(_item.id)
                    else:
                        return_data.append(_item)

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