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

from server.utils.db import DataBase, pdbc


class EditVmachine(DataBase):
    @pdbc
    def batch_update_status(self, table, batch_data, namespace=None, broadcast=False):
        """
        批量更新虚拟机数据
        :param table: table Model
        :param batch_data: Type[list] vmachines name
        :param namespace:namespace
        :param broadcast:broadcast
        """
        vmachines = self._table.query.filter(self._table.name.in_(batch_data)).all()
        if not vmachines:
            raise ValueError("Related vmachines does not exist.")
        for vmachine in vmachines:
            update_data = self._data.get(vmachine.name)
            for key, value in update_data.items():
                if value is not None:
                    setattr(vmachine, key, value)
            vmachine.add_update(table, namespace, broadcast)
