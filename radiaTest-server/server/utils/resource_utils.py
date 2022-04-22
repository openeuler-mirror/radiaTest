import json, os
from flask import jsonify
from server.utils.db import Insert, Delete
from server.utils.response_util import RET
from server.model.milestone import Milestone
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from server.utils.permission_utils import PermissionManager
from server.utils.table_adapter import TableAdapter

class ResourceManager:
    def __init__(self, table_name) -> None:
        self._table = getattr(TableAdapter, table_name)
        self.table_name = table_name
    
    def add_permission(self, file_name, body, item_id):
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager().get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + self.table_name + os.sep + file_name,
            item_id
        )
        PermissionManager().generate(allow_list, deny_list, body)

    def add(self, file_name, body):
        try:
            item_id = Insert(self._table, body).insert_id(self._table, "/"+self.table_name)
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError(str(e))
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager().get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + self.table_name + os.sep + file_name,
            item_id
        )
        PermissionManager().generate(allow_list, deny_list, body)
        
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    
    def add_v2(self, file_name, body):
        try:
            item_id = Insert(self._table, body).insert_id(self._table, "/"+self.table_name)
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError(str(e))
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager().get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + file_name,
            item_id
        )
        PermissionManager().generate(allow_list, deny_list, body)
        
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    
    def del_single(self, resource_id):
        Delete(self._table, {"id":resource_id}).single(self._table, "/" + self.table_name)
        PermissionManager().clean("/api/v1/"+ self.table_name + "/", [resource_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    #级联删除，cascase_table存在关联数据，如果cascade_del=True，允许删除，否则不能删除
    def del_cascade_single(self, resource_id, cascade_table, filter_params, cascade_del: bool):
        _cascades = cascade_table.query.filter(*filter_params).all()
        if _cascades:
            if not cascade_del:
                return jsonify(
                    error_code=RET.CASCADE_OP_ERR,
                    error_msg="Delete failed, there are multiple {} under {}.".format(cascade_table.__tablename__, self.table_name)
                )
            else:
                cas_ids = [cas.id for cas in _cascades]
                PermissionManager().clean("/api/v1/"+ cascade_table.__tablename__ + "/", cas_ids)

        Delete(self._table, {"id":resource_id}).single(self._table, "/" + self.table_name)
        PermissionManager().clean("/api/v1/"+ self.table_name + "/", [resource_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    
    def del_batch(self, resource_ids: list):
        Delete(self._table, {"id":resource_ids}).batch(self._table, "/" + self.table_name)
        PermissionManager().clean("/api/v1/"+ self.table_name + "/", resource_ids)
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )


