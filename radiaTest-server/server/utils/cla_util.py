# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2022-04-07 21:28:45
# @Last Modified by:   Your name
import json
from flask import current_app
from server.utils.requests_util import do_request
from pydantic import BaseModel, Field, validator
from typing import Optional


class Cla(object):

    @staticmethod
    def is_cla_signed(cla_info, params, body):
        url = cla_info.get("cla_verify_url")
        request_type = cla_info.get("cla_request_type").lower()
        flag_params, params = Cla.analysis_params(cla_info.get("cla_verify_params"), params)
        flag_body, body = Cla.analysis_params(cla_info.get("cla_verify_body"), body)
        if not all([flag_params, flag_body]):
            return False
        params = params if request_type in ["get", "delete"] else None
        data = params if request_type in ["post", "put"] else None
        resp = {}
        r = do_request(request_type.lower(), url, body=data, params=params, obj=resp)
        if r != 0:
            return False
        return Cla.judge_pass_flag(resp, cla_info.get("cla_pass_flag"))

    @staticmethod
    def analysis_params(validator_params, params):
        if not validator_params or not isinstance(validator_params, dict):
            return True, params
        cla = "class ClaModel(BaseModel):\n"
        for key, value in validator_params.items():
            cla = cla + f"    {key}: {value}\n"
        loc = {}
        try:
            exec(cla, {"BaseModel": BaseModel}, loc)
            cla_model = loc["ClaModel"]
            params = cla_model(**params)
            return True, params.dict()
        except Exception as e:
            current_app.logger.error(f"analysis cla params errpr: {e}")
            return False, {}

    @staticmethod
    def judge_pass_flag(resp_dict, pass_flag):
        result = pass_flag.split("=")[1].strip()
        key = pass_flag.split("=")[0].strip()
        for temp_key in key.split("."):
            resp_dict = resp_dict.get(temp_key, {})
        if str(resp_dict).lower() == str(result).lower():
            return True
        current_app.logger.error(f"judge cla pass condition error: {str(resp_dict).lower()} != {str(result).lower()}")
        return False


class ClaBaseSchema(BaseModel):
    cla_verify_params: Optional[str] = {}
    cla_verify_body: Optional[str] = {}

    @validator("cla_verify_params")
    def validator_cla_verify_params(cls, v):
        if not v:
            return {}
        try:
            return json.loads(v)
        except Exception as e:
            current_app.logger.error(f"json --> dict error {e}")
            return {}

    @validator("cla_verify_body")
    def validator_cla_verify_body(cls, v):
        if not v:
            return {}
        try:
            return json.loads(v)
        except Exception as e:
            current_app.logger.error(f"json --> dict error {e}")
            return {}


class ClaSignSchema(ClaBaseSchema):
    organization_id: int


class ClaShowUserSchema(ClaBaseSchema):
    organization_id: int = Field(alias='id')
    organization_name: str = Field(alias="name")
    organization_description: Optional[str] = Field(alias="description")
    organization_avatar: Optional[str] = Field(alias="avatar_url")

    cla_sign_url: Optional[str]


class ClaShowAdminSchema(ClaShowUserSchema):
    cla_verify_url: Optional[str]
    cla_request_type: Optional[str]
    cla_pass_flag: Optional[str]
    enterprise_id: Optional[str]
    oauth_client_id: Optional[str]
    oauth_client_secret: Optional[str]
    oauth_scope: Optional[str]
    authority: Optional[str]
    oauth_login_url: Optional[str]
    oauth_get_token_url: Optional[str]
    oauth_get_user_info_url: Optional[str]
