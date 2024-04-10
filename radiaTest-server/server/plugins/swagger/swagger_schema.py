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
# @Date    : 2023/09/19
# @License : Mulan PSL v2
#####################################
from enum import Enum
from typing import List, Optional, Dict


from pydantic import BaseModel

#  参考文档https://codeleading.com/article/75955850205/


class TagDict(BaseModel):
    name: str
    description: str


class Method(str, Enum):
    get = "get"
    post = "post"
    put = "put"
    delete = "delete"
    options = "options"
    head = "head"
    patch = "patch"
    trace = "trace"


class ExternalDocs(BaseModel):
    url: str
    description: str


class RequestBody(BaseModel):
    content: dict = {"application/json": {"schema": dict}}


class BaseResponse(BaseModel):
    code: int = 200
    data: dict = {}
    error_code: str = "2000"
    error_msg: str = "OK"


class Description(BaseModel):
    description: str = ""


class SchemaType(Enum):
    int = {"type": "integer", "format": "int32"}
    float = {"type": "number", "format": "float"}
    string = {"type": "string"}
    bool = {"type": "boolean"}
    # 路径参数暂时无需以下数据类型
    bytes = {"type": "string", "format": "byte"}
    long = {"type": "integer", "format": "int64"}
    double = {"type": "number", "format": "double"}
    binary = {"type": "string", "format": "binary"}  # 任意 8进制序列
    date = {"type": "string", "format": "date"}
    datetime = {"type": "string", "format": "date-time"}
    password = {"type": "string", "format": "password"}  # 告知输入界面不应该明文显示输入信息。


class EnumParameter(Enum):
    class EnumHeaderName(str, Enum):
        accept = "Accept"
        content_type = "Content-Type"
        authorization = "Authorization"

    class ParameterName(BaseModel):
        name: str

    class ParameterRequired(Enum):
        true = True
        false = False

    query = {
        "name": ParameterName,
        "in": "query",
        "description": Description,
        "required": ParameterRequired,
        "style": "form",
        "explode": True,
        "schema": SchemaType,
    }
    header = {
        "name": EnumHeaderName,
        "in": "header",
        "description": Description,
        "required": ParameterRequired,
        "style": "simple",
        "explode": False,
        "schema": SchemaType,
    }
    path = {
        "name": ParameterName,
        "in": "path",
        "description": Description,
        "required": ParameterRequired,
        "style": "simple",
        "explode": False,
        "schema": SchemaType,
    }
    cookie = {
        "name": ParameterName,
        "in": "cookie",
        "description": Description,
        "required": ParameterRequired,
        "style": "form",
        "explode": True,
        "schema": SchemaType,
    }


class ApiDict(BaseModel):
    url: str
    method: Method
    tags: List[TagDict]
    summary: Optional[str]
    description: Description
    externalDocs: Optional[ExternalDocs]
    deprecated: bool = False  # 声明该接口已被废弃
    parameters: List[EnumParameter] = []
    requestBody: Optional[RequestBody]
    responses: Dict[str, BaseResponse]

