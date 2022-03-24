import json, yaml, os
from flask import g, jsonify
from server.utils.response_util import RET

from server import redis_client
from server.utils.redis_util import RedisKey
from server.model import Product, Group, ReUserGroup
from server.utils.db import Insert, Delete, Precise
from server.utils.permission_utils import PermissionManager
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

class CreateProduct:
    @staticmethod
    def run(body):
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split("/")[-1], "")
        try:
            product_id = Insert(Product, body).insert_id(Product, '/product')
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError(str(e))
        allow_list, deny_list = PermissionManager().get_api_list(cur_dir + "api_infos.yaml", product_id)
        if body.get("group_id"):
            PermissionManager().generate(allow_list, deny_list, body.get("permission_type"), group_id=body.get("group_id"))
        else:
            PermissionManager().generate(allow_list, deny_list, body.get("permission_type"))
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )

class DeleteProduct:
    @staticmethod
    def batch(body):
        Delete(Product, body).batch(Product, '/product')
        PermissionManager().clean("/api/v1/product/", body.get("id"))
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )

    @staticmethod
    def single(product_id):
        Delete(Product, {"id":product_id}).single(Product, '/product')
        PermissionManager().clean("/api/v1/product/", [product_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
