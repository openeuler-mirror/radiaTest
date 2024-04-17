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

import re

from werkzeug.security import generate_password_hash, check_password_hash

from server.model import BaseModel
from server import db, casbin_enforcer
from server.model.password_rule import PasswordRule


class Admin(db.Model, BaseModel):
    __tablename__ = 'administrator'
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    account = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    @property
    def password(self):
        raise AttributeError('password is not allowed reading')

    @password.setter
    def password(self, password):
        pattern = (
            r"^(?=(?:.*[a-z])?)(?=(?:.*[A-Z])?)(?=(?:.*\d)?)(?=(?:.*[!@#$%^&*()-_+=])?)[a-zA-Z\d!^~@#$%^&*()-_+=]+$"
        )
        if not re.match(pattern, password):
            raise ValueError('The password complexity does not meet the requirements')

        rule_exists = PasswordRule.query.filter_by(rule=password).first()
        if rule_exists:
            raise ValueError('password is weak')

        self.password_hash = generate_password_hash(password)

    def check_password_hash(self, password):
        return check_password_hash(self.password_hash, password)

    def add_update(self, table=None, namespace=None, broadcast=False):
        casbin_enforcer.adapter.add_policy(
            "g",
            "g",
            ["admin_%s" % (self.id), "root"]
        )
        return super().add_update(table, namespace)

    def delete(self, table=None, namespace=None, broadcast=False):
        casbin_enforcer.adapter.remove_policy(
            "g",
            "g",
            ["admin_%s" % (self.id), "root"]
        )
        return super().delete(table, namespace)
