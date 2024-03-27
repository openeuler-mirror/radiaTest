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

import json

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, validator


class MessageModel(BaseModel):
    id: Optional[int]
    data: str
    level: int
    from_id: str
    is_delete: bool
    has_read: bool
    type: int
    create_time: datetime

    @validator('data')
    def validate_data(cls, v):
        try:
            return json.loads(v)
        except ValueError as e:
            return dict()


class MessageCallBack(BaseModel):
    msg_id: int
    access: bool


class TextMessageModel(BaseModel):
    data: dict
    to_ids: list
