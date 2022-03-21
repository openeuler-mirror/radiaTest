import json
from paramiko import SSHException
import requests
from typing import List

from flask import current_app, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db
from server.utils.response_util import RET
from server.model.permission import ReScopeRole, Role, Scope
from server.utils.response_util import RET
from server.utils.db import Insert, Precise


class PermissionManager:
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

    def generate(self, scope_datas_allow, scope_datas_deny, permission_type, owner_id = None):
        role = Precise(
            Role,
            {
                "name": "root" if permission_type == "public" else owner_id,
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