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

from pydantic import BaseModel, validator, root_validator


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

        if values['new_password'] != values['re_new_password']:
            raise ValueError('The passwords entered twice are different')
        return values
