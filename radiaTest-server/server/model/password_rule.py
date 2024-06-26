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

from server import db
from server.model import BaseModel


class PasswordRule(db.Model, BaseModel):
    __tablename__ = "password_rule"

    id = db.Column(db.Integer, primary_key=True)
    rule = db.Column(db.String(255), nullable=False)

    def to_json(self):
        return_data = {
            "id": self.id,
            "rule": self.rule
        }
        return return_data
