# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : hukun66
# @email   : hu_kun@hoperun.com
# @Date    : 2023/09/15
# @License : Mulan PSL v2
#####################################
import logging
import os
import re
import threading
import uuid
from copy import deepcopy
from functools import wraps
from pathlib import Path
from typing import Optional, List, Dict

import yaml
from flask import current_app
from flask_sqlalchemy.model import Model as sqlalchemyModel
from sqlalchemy.sql.sqltypes import DateTime, Integer, String, Boolean, Float
from pydantic import BaseModel


from server.plugins.swagger.swagger_schema import BaseResponse, SchemaType


class SwaggerJsonAdapt(object):
    """
    swagger.json生成适配器
    """
    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not getattr(cls, "_instance"):
            with cls._instance_lock:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, swagger_file=None):

        self.api_dict = {}
        self.tag_dict = {}
        self.api_info_map = {}
        self.swagger_file = Path(swagger_file) if swagger_file else Path(
            current_app.config.get("SWAGGER_DIST_PATH")).joinpath(current_app.config.get("SWAGGER_YAML_FILE"))
        self.root_path = Path(__file__).parent
        self.openai_yaml = self.root_path.joinpath("openapi.yaml")
        self.swagger_json = {}

    def add_query_parameters(self, schema_model):
        if not isinstance(schema_model, type) or not issubclass(schema_model, BaseModel):
            return schema_model
        data = []
        schema_json = schema_model.schema()
        self.update_definitions(schema_json)
        for name, filed_schema in schema_json["properties"].items():
            parameter = {
                "name": name,
                "in": "query",
                "required": True if name in schema_json.get("required", []) else False,
                "style": "form",
                "explode": True,
                "description": filed_schema.get("title", ""),
                "schema": filed_schema
            }
            data.append(parameter)
        return data

    def add_request_body(self, schema_model):
        if not isinstance(schema_model, type) or not issubclass(schema_model, BaseModel):
            return schema_model
        schema_json = schema_model.schema()
        self.update_definitions(schema_json)
        data = {
            "description": "",
            "content": {
                "application/json":
                    {"schema": schema_json}
            },
            "required": True
        }
        return data

    def add_responses(self, schema_model):
        if not isinstance(schema_model, type) or not issubclass(schema_model, BaseModel):
            return schema_model
        schema_json = schema_model.schema()
        self.update_definitions(schema_json)
        code = schema_json["properties"].pop("code", "200")
        default_schema = {
            "description": "",
            "type": "object",
            "properties": {
                "data": schema_json,
                "error_code": {
                    "type": "string"
                },
                "error_msg": {
                    "default": "OK",
                    "type": "string"
                }
            }
        }
        data = {
            str(code): {
                "description": "",
                "content": {
                  "application/json": {
                    "schema": default_schema
                  }}}}
        return data

    @staticmethod
    def get_default_responses():
        return {
            "200": {
                "description": "success",
                "content": {
                    "application/json":
                        {"schema": {"$ref": "#/components/schemas/default_responses"}}
                },
            }
        }

    def add_api(self, api_json):
        tag = api_json.get("tag")
        if tag["name"] not in self.tag_dict:
            self.tag_dict[tag["name"]] = tag["description"]

        if api_json.get("method"):
            api_swagger_info = {
                "security": [{"api_key": []}],
                "tags": [tag["name"]],
                "summary": api_json.get("summary", ''),
                "externalDocs": api_json.get("externalDocs"),
                "responses": self.add_responses(api_json.get("response_data_schema")) if
                api_json.get("response_data_schema") else self.get_default_responses(),
            }
            if api_json.get("query_schema_model"):
                api_swagger_info["parameters"] = self.add_query_parameters(api_json["query_schema_model"])
            if api_json.get("request_schema_model"):
                api_swagger_info["requestBody"] = self.add_request_body(api_json["request_schema_model"])
            origin_url = api_json["url"]
            url = api_json["url"]
            # 路径参数获取与格式化，暂时只支持简单类型 string、int、float、bool
            path_params = re.findall(r"<(?P<field_type>\w+):(?P<field_name>\w+)>", origin_url)
            for field_type, field_name in path_params:
                if not api_swagger_info.get("parameters"):
                    api_swagger_info["parameters"] = []
                if field_type not in ["string", "int", "float", "bool"]:
                    logging.warning(f"[warning]不支持{field_type}类型的路径参数解析,{origin_url}已忽略！")
                    continue
                url = url.replace(f"<{field_type}:{field_name}>", "{%s}" % field_name)
                api_swagger_info["parameters"].append({
                    "name": field_name,
                    "in": "path",
                    "required": True,
                    "style": "simple",
                    "explode": True,
                    "description": field_name,
                    "schema": getattr(SchemaType, field_type).value
                })
            # 未申明类型的参数，固定为string
            for field_name in re.findall(r"<(?P<field_name>\w+)>", origin_url):
                if not api_swagger_info.get("parameters"):
                    api_swagger_info["parameters"] = []
                url = url.replace(f"<{field_name}>", "{%s}" % field_name)
                api_swagger_info["parameters"].append({
                    "name": field_name,
                    "in": "path",
                    "required": True,
                    "style": "simple",
                    "explode": True,
                    "description": field_name,
                    "schema": getattr(SchemaType, "string").value
                })
            method = api_json["method"].lower()
            api_swagger_info["operationId"] = url.replace("/", "_").replace("{", "").replace("}", "") + f"_{method}"
            if url in self.swagger_json["paths"]:
                self.swagger_json["paths"][url][method] = api_swagger_info
            else:
                self.swagger_json["paths"][url] = {
                    method: api_swagger_info
                }

    def load_swagger_json(self):
        if self.swagger_file.exists():
            with open(self.swagger_file, "r", encoding="utf-8") as f:
                swagger_json = yaml.safe_load(f)
        else:
            swagger_json = {}
        with open(self.openai_yaml, "r", encoding="utf-8") as f:
            swagger_json.update(yaml.safe_load(f))
        self.swagger_json = swagger_json

    @staticmethod
    def adapt_ref_address(schema_dict):
        # 多重引用地址适配
        if "properties" in schema_dict and isinstance(schema_dict.get("properties"), dict):
            for name, info in schema_dict["properties"].items():
                if info.get("type") == "array":
                    if "$ref" in info["items"]:
                        info["items"]["$ref"] = info["items"]["$ref"].replace("definitions", "components/schemas")
                else:
                    if "$ref" in info:
                        info["$ref"] = info["$ref"].replace("definitions", "components/schemas")

    def update_definitions(self, schema_dict):
        if isinstance(schema_dict, dict):
            if schema_dict.get("definitions"):
                definitions = schema_dict.pop("definitions")
                # 更新所有schemas引用
                update_schemas = {}
                # 重名参数改名
                for definition, definition_info in definitions.items():
                    self.adapt_ref_address(definition_info)  # 多重引用地址处理
                    if definition in self.swagger_json["components"]["schemas"]:
                        update_schemas[definition] = {
                            "unique_name": definition + "_" + str(uuid.uuid4()).replace('-', ''),
                            "info": definition_info,
                        }
                    else:
                        update_schemas[definition] = {
                            "unique_name": definition,
                            "info": definition_info,
                        }
                for definition, info in update_schemas.items():
                    self.swagger_json["components"]["schemas"][info["unique_name"]] = info["info"]
                # 替换所有schemas引用地址位置至components/schemas
                for name, info in schema_dict["properties"].items():
                    if info.get("type") == "array":
                        if "$ref" in info["items"]:
                            definition_name = info["items"]["$ref"].replace("#/definitions/", "")
                            info["items"]["$ref"] = f'#/components/schemas/' \
                                                    f'{update_schemas[definition_name]["unique_name"]}'
                    else:
                        if "$ref" in info:
                            definition_name = info["$ref"].replace("#/definitions/", "")
                            info["$ref"] = f'#/components/schemas/{update_schemas[definition_name]["unique_name"]}'

    def save_swagger_yaml(self):
        self.swagger_json["tags"].extend(
            [{"name": name, "description": value} for name, value in self.tag_dict.items()])
        with open(self.swagger_file, "w", encoding="utf-8") as f:
            yaml.dump(self.swagger_json, f, allow_unicode=True)

    def swagger_wrapper(self, api_json):
        def wrapper(func):
            @wraps(func)
            def inner_wrapper(*args, **kwargs):
                self.add_api(api_json)
                return func(*args, **kwargs)
            return inner_wrapper
        return wrapper

    def save_api_info_map(self):
        # 限制保存映射次数
        with self._instance_lock:
            # 删除旧的swagger_file
            if self.swagger_file.exists():
                os.remove(self.swagger_file.absolute())
            self.load_swagger_json()
            for _, resource_info in self.api_info_map.items():
                for _, func_info in resource_info.items():
                    for _, api_schema_dict in func_info.items():
                        url = api_schema_dict.get("url")
                        method = api_schema_dict.get("method")
                        if url and method:
                            for url_item in url:
                                api_dict = deepcopy(api_schema_dict)
                                api_dict["url"] = url_item
                                self.add_api(api_dict)
            self.save_swagger_yaml()

    def api_schema_model_map(self, api_schema_dict):
        model_name = api_schema_dict.get("__module__")
        resource_name = api_schema_dict.get("resource_name")
        func_name = api_schema_dict.get("func_name")

        if model_name not in self.api_info_map:
            self.api_info_map[model_name] = {}
        if resource_name not in self.api_info_map[model_name]:
            self.api_info_map[model_name][resource_name] = {}
        if func_name in self.api_info_map[model_name][resource_name]:
            logging.warning(
                f"[warning] {model_name} {resource_name} {func_name} is repeat, overwritten old api info!!!")
        self.api_info_map[model_name][resource_name][func_name] = api_schema_dict

        def wrapper(func):
            @wraps(func)
            def inner_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return inner_wrapper

        return wrapper

    @staticmethod
    def get_db_model_fields(db_model):
        if not isinstance(db_model, type) or not issubclass(db_model, sqlalchemyModel):
            return {}
        return {col.name: col.type for col in db_model.__table__.columns}

    @staticmethod
    def get_schema_type(field_type):
        if isinstance(field_type, Integer):
            return getattr(SchemaType, "int").value
        elif isinstance(field_type, Float):
            return getattr(SchemaType, "float").value
        elif isinstance(field_type, Boolean):
            return getattr(SchemaType, "bool").value
        elif isinstance(field_type, DateTime):
            return getattr(SchemaType, "datetime").value
        elif isinstance(field_type, String):
            return getattr(SchemaType, "string").value
        else:
            return getattr(SchemaType, "string").value

    def get_query_schema_by_db_model(self, db_model, require_list=None):
        fields = self.get_db_model_fields(db_model)
        if not require_list:
            require_list = []
        data = []
        for field, field_type in fields.items():
            data.append({
                "name": field,
                "in": "query",
                "required": True if field in require_list else False,
                "style": "form",
                "explode": True,
                "description": field,
                "schema": self.get_schema_type(field_type)
            })
        return data

    def get_request_schema_by_db_model(self, db_model, require_list=None):
        fields = self.get_db_model_fields(db_model)
        if not require_list:
            require_list = []
        required = []
        if not fields:
            return {}
        schema = {
                "properties": {},
                "title": "Schema",
                "type": "object"
              }

        for field, field_type in fields.items():
            field_schema = {"title": field}
            field_schema.update(self.get_schema_type(field_type))
            schema["properties"][field] = field_schema
            if field in require_list:
                required.append(field)
        if required:
            schema["required"] = required
        return {
            "description": "",
            "content": {
                "application/json":
                    {"schema": schema}
            },
            "required": True
        }


if __name__ == '__main__':
    class FeatureApplySchema(BaseModel):
        strategy_template_id: Optional[int]
        strategy_node_id: Optional[int]
        node_ids: List[int]
        node_int: Dict[str, int]
        node_int: dict = {"test": 1}

    from enum import Enum

    class EnumsTaskExecutorType(str, Enum):
        """Another Enums class"""

        PERSON = "PERSON"
        GROUP = "GROUP"


    class BaseEnum(Enum):
        @classmethod
        def code(cls, attr):
            if hasattr(cls, attr):
                return getattr(cls, attr).value
            else:
                return None

    class EnumsTaskType(str, Enum):
        """Another Enums class"""

        PERSON = "PERSON"
        GROUP = "GROUP"
        ORGANIZATION = "ORGANIZATION"
        VERSION = "VERSION"


    class AddTaskSchema(BaseModel):
        title: str
        type: EnumsTaskType
        status_id: int
        group_id: int = None
        executor_type: EnumsTaskExecutorType
        executor_id: str
        start_time: str
        deadline: str
        is_version_task: bool = False
        parent_id: List[int] = None
        child_id: List[int] = None
        keywords: str = None
        abstract: str = None
        abbreviation: str = None
        content: str = None
        milestone_id: int = None
        case_id: int = None
        is_single_case: bool = False
        is_manage_task: bool = False
        case_node_id: int = None

    user_tag = {
        "name": "用户",
        "description": "用户相关接口",
    }

    API_JSON = {
        "url": "/get/users",
        "method": "post",
        "tag": user_tag,
        "__module__": "user_tag.__module__",  # 获取当前接口所在模块
        "resource_name": "Task",  # 当前接口视图函数名
        "summary": "",
        "externalDocs": {"description": "", "url": ""},
        "request_schema_model": AddTaskSchema,
    }
    adapt = SwaggerJsonAdapt("demo.yaml")
    adapt.load_swagger_json()
    adapt.api_schema_model_map(API_JSON)
    adapt.save_api_info_map()


