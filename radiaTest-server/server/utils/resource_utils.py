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

import os

from flask import jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server.utils.db import Insert, Delete
from server.utils.response_util import RET
from server.utils.permission_utils import PermissionManager
from server.utils.table_adapter import TableAdapter


class ResourceManager:
    def __init__(self, table_name, api_ver=None, creator_id=None, org_id=None) -> None:
        self._table = getattr(TableAdapter, table_name)
        self.table_name = table_name
        self.api_ver = "/api/v1"
        if api_ver:
            self.api_ver = "/api/" + api_ver
        self.creator_id = creator_id
        self.org_id = org_id

    def add_permission(self, file_name, body, item_id):
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(
            os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager.get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + self.table_name + os.sep + file_name,
            item_id
        )
        PermissionManager(self.creator_id, self.org_id).generate(allow_list, deny_list, body)

    def add(self, file_name, body):
        try:
            item_id = Insert(self._table, body).insert_id(
                self._table, "/"+self.table_name)
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError("insert db error:{}".format(e)) from e
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(
            os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager.get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + self.table_name + os.sep + file_name,
            item_id
        )
        PermissionManager().generate(allow_list, deny_list, body)

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully.",
            data={"id": item_id}
        )

    def add_v2(self, file_name, body):
        try:
            item_id = Insert(self._table, body).insert_id(
                self._table, "/"+self.table_name)
        except (IntegrityError, SQLAlchemyError) as e:
            raise RuntimeError("insert db method2 error:{}".format(e)) from e
        cur_file_dir = os.path.abspath(__file__)
        cur_dir = cur_file_dir.replace(cur_file_dir.split(
            os.sep)[-1], "").replace("utils"+os.sep, "")
        allow_list, deny_list = PermissionManager.get_api_list(
            self.table_name,
            cur_dir + "apps" + os.sep + file_name,
            item_id
        )
        PermissionManager().generate(allow_list, deny_list, body)

        return jsonify(
            error_code=RET.OK,
            error_msg="Request processed successfully.",
            data={"id": item_id}
        )

    def del_single(self, resource_id):
        Delete(self._table, {"id": resource_id}).single(
            self._table, "/" + self.table_name)
        PermissionManager.clean(self.api_ver + "/" +
                                  self.table_name + "/", [resource_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
    # 级联删除，cascase_table存在关联数据，如果cascade_del=True，允许删除，否则不能删除

    def del_cascade_single(self, resource_id, cascade_table, filter_params, cascade_del: bool):
        _cascades = cascade_table.query.filter(*filter_params).all()
        if _cascades:
            if not cascade_del:
                return jsonify(
                    error_code=RET.CASCADE_OP_ERR,
                    error_msg="Delete failed, there are multiple {} under {}.".format(
                        cascade_table.__tablename__, self.table_name)
                )
            else:
                cas_ids = [cas.id for cas in _cascades]
                PermissionManager.clean(self.api_ver + "/" +
                                          cascade_table.__tablename__ + "/", cas_ids)

        Delete(self._table, {"id": resource_id}).single(
            self._table, "/" + self.table_name)
        PermissionManager.clean(self.api_ver + "/" +
                                  self.table_name + "/", [resource_id])
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )

    def del_batch(self, resource_ids: list):
        Delete(self._table, {"id": resource_ids}).batch(
            self._table, "/" + self.table_name)
        PermissionManager.clean(self.api_ver + "/" + self.table_name + "/", resource_ids)
        return jsonify(
            error_code=RET.OK, error_msg="Request processed successfully."
        )
