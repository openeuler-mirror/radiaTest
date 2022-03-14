from flask import jsonify, current_app
from server import db
from server.model.permission import ReScopeRole, Role, Scope
from server.utils.response_util import RET
from server.utils.db import Insert, Precise, Like
from typing import List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

class PermissionManager:
    def insertscope(self, scope_datas):
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
    
        scope_allow_ids = insertscope(scope_datas_allow)
        _ = insertscope(scope_datas_deny)

        for _id in scope_allow_ids:
            scope_role_data = {
                "scope_id": _id,
                "role_id": role.id
            }
            Insert(ReScopeRole, scope_role_data).single()
    
    def clean(self, uri_part, item_ids: List[int]):
        for item_id in item_ids:
            filter_str = uri_part + str(item_id)
            filter_params = []
            filter_params.append(Scope.uri.like(f'%{filter_str}%'))
            scopes = Scope.query.filter(*filter_params).all()
            for scope in scopes:
                db.session.delete(scope)
                db.session.commit()
