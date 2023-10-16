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

from flask_restful import Resource
from flask_pydantic import validate

from server import swagger_adapt
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.celerytask import CeleryTaskCreateSchema, CeleryTaskQuerySchema
from .handler import CeleryTaskHandler


def get_celery_task_tag():
    return {
        "name": "celery任务",
        "description": "celery任务相关接口",
    }


class CeleryTaskEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_celery_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "CeleryTaskEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_celery_task_tag(),  # 当前接口所对应的标签
        "summary": "查询当前用户的所有celery任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CeleryTaskQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, query: CeleryTaskQuerySchema):
        return CeleryTaskHandler.get_all(query)

    @auth.login_required
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_celery_task_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "CeleryTaskEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_celery_task_tag(),  # 当前接口所对应的标签
        "summary": "创建celery任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CeleryTaskCreateSchema,   # 当前接口查询参数schema校验器
    })
    def post(self, body: CeleryTaskCreateSchema):
        return CeleryTaskHandler.create(body)
