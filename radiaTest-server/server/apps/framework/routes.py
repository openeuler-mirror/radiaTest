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

from flask import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import RET, workspace_error_collect
from server.utils.response_util import response_collect
from server.model.framework import Framework, GitRepo
from server.utils.db import Edit
from server.schema.framework import FrameworkBase, FrameworkQuery
from server.utils.resource_utils import ResourceManager
from server.utils.permission_utils import GetAllByPermission
from server import casbin_enforcer, swagger_adapt


def get_framework_tag():
    return {
        "name": "测试框架",
        "description": "测试框架相关接口",
    }


class FrameworkEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_framework_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FrameworkEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_framework_tag(),  # 当前接口所对应的标签
        "summary": "添加测试框架",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": FrameworkBase
    })
    def post(self, body: FrameworkBase):
        return ResourceManager("framework").add("api_infos.yaml", body.__dict__)

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_framework_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FrameworkEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_framework_tag(),  # 当前接口所对应的标签
        "summary": "查询测试框架",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": FrameworkQuery
    })
    def get(self, workspace: str, query: FrameworkQuery):
        filter_params = GetAllByPermission(Framework, workspace).get_filter()
        if query.name:
            filter_params.append(
                Framework.name.like(f'%{query.name}%')
            )
        if query.url:
            filter_params.append(
                Framework.url.like(f'%{query.url}%')
            )
        if query.adaptive:
            filter_params.append(
                Framework.adaptive == query.adaptive
            )

        frameworks = Framework.query.filter(*filter_params).all()
        if not frameworks:
            return jsonify(error_code=RET.OK, error_msg="OK", data=[])

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[
                _framework.to_json() for _framework in frameworks
            ]
        )


class FrameworkItemEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_framework_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FrameworkItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_framework_tag(),  # 当前接口所对应的标签
        "summary": "删除测试框架",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, framework_id):
        return ResourceManager("framework").del_cascade_single(framework_id, GitRepo,
                                                               [GitRepo.framework_id == framework_id], False)

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_framework_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FrameworkItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_framework_tag(),  # 当前接口所对应的标签
        "summary": "修改测试框架",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": FrameworkQuery
    })
    def put(self, framework_id, body: FrameworkQuery):
        _body = {
            **body.__dict__,
            "id": framework_id,
        }

        return Edit(Framework, _body).single(Framework, "/framework")

    @auth.login_required
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    @swagger_adapt.api_schema_model_map({
        "__module__": get_framework_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "FrameworkItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_framework_tag(),  # 当前接口所对应的标签
        "summary": "获取测试框架信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, framework_id):
        framework = Framework.query.filter_by(id=framework_id).first()
        if not framework:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the framework does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=framework.to_json()
        )
