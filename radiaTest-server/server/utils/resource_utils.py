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

    def add(self, file_name, body):
        try:
            item_id = Insert(self._table, body).insert_id()
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError(str(e))
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager().get_api_list(cur_dir + "apps" + os.sep + self.table_name + os.sep + file_name, item_id)
        PermissionManager().generate(allow_list, deny_list, body)
        
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    
    def del_single(self, resource_id):
        Delete(self._table, {"id":resource_id}).single()
        PermissionManager().clean("/api/v1/"+ self.table_name + "/", [resource_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    
    def del_batch(self, resource_ids: list):
        Delete(self._table, {"id":resource_ids}).batch()
        PermissionManager().clean("/api/v1/"+ self.table_name + "/", resource_ids)
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )


