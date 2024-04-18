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

from pydantic import BaseModel, validator, root_validator

from server.model.password_rule import PasswordRule


class LoginSchema(BaseModel):
    account: str
    password: str


class ChangePasswdSchema(BaseModel):
    account: str
    old_password: str
    new_password: str
    re_new_password: str

    @validator('account')
    def v_account(cls, v):
        if len(v) < 5 or len(v) > 30:
            raise ValueError('account length should be greater than 5 and less than 30')
        return v

    @root_validator
    def v_password(cls, values):
        if len(values['old_password']) < 8 or len(values['new_password']) < 8 or len(values['re_new_password']) < 8:
            raise ValueError('password length should be greater than 8')

        if values['new_password'] == values['old_password']:
            raise ValueError('new password same with old password')

        if values['new_password'] != values['re_new_password']:
            raise ValueError('The passwords entered twice are different')

        pattern = (
            r"^(?=(?:.*[a-z])?)(?=(?:.*[A-Z])?)(?=(?:.*\d)?)(?=(?:.*[!@#$%^&*()-_+=])?)[a-zA-Z\d!^~@#$%^&*()-_+=]+$"
        )
        if not re.match(pattern, values['new_password']):
            raise ValueError('The password complexity does not meet the requirements')

        rule_exists = PasswordRule.query.filter_by(rule=values['new_password']).first()
        if rule_exists:
            raise ValueError('password is weak')

        return values


class AddRuleSchema(BaseModel):
    rule: str

    @validator('rule')
    def v_rule(cls, v):
        if not v:
            raise ValueError('rule is empty not support')

        if ' ' in v:
            raise ValueError('space in rule is not support')
        return v
