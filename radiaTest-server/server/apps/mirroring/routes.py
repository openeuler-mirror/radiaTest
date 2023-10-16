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

from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server import swagger_adapt
from server.utils.db import Insert, Delete, Edit, Select
from server.utils.response_util import response_collect
from server.utils.auth_util import auth

from server.model.mirroring import IMirroring, QMirroring, Repo
from server.utils.resource_utils import ResourceManager
from server.schema.base import DeleteBaseModel
from server.schema.mirroring import (
    IMirroringBase,
    IMirroringUpdate,
    QMirroringBase,
    QMirroringUpdate,
    RepoCreate,
    RepoUpdate,
)


def get_mirroring_tag():
    return {
        "name": "mirroring镜像",
        "description": "mirroring镜像相关接口",
    }


class IMirroringItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "删除镜像",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, i_mirroring_id):
        return ResourceManager("i_mirroring").del_single(i_mirroring_id)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "获取镜像信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, i_mirroring_id):
        return Select(IMirroring, {"id":i_mirroring_id}).single()

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "修改镜像",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": IMirroringUpdate
    })
    def put(self, i_mirroring_id, body: IMirroringUpdate):
        _body = body.__dict__
        _body.update({"id": i_mirroring_id})
        return Edit(IMirroring, _body).single(IMirroring, '/imirroring')


class IMirroringEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "IMirroringEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "创建镜像",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": IMirroringBase
    })
    def post(self, body: IMirroringBase):
        return Insert(IMirroring, body.__dict__).single(IMirroring, '/imirroring')


class PreciseGetIMirroring(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PreciseGetIMirroring",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "获取镜像列表，通过镜像信息精确查询",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(IMirroring)
    })
    def get(self):
        body = request.args.to_dict()
        return Select(IMirroring, body).precise()


class QMirroringItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "QMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "删除qemu镜像",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, q_mirroring_id):
        return ResourceManager("q_mirroring").del_single(q_mirroring_id)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "QMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "获取qemu镜像信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(QMirroring)
    })
    def get(self, q_mirroring_id):
        return Select(QMirroring, {"id":q_mirroring_id}).single()

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "QMirroringItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "编辑qemu镜像信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": QMirroringUpdate
    })
    def put(self, q_mirroring_id, body: QMirroringUpdate):
        _body = body.__dict__
        _body.update({"id": q_mirroring_id})
        return Edit(QMirroring, _body).single(QMirroring, '/qmirroring')


class QMirroringEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "QMirroringEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "创建qemu镜像信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": QMirroringBase
    })
    def post(self, body: QMirroringBase):
        return Insert(QMirroring, body.__dict__).single(QMirroring, '/qmirroring')


class PreciseGetQMirroring(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PreciseGetQMirroring",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "精确查询qemu镜像信息列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(QMirroring)
    })
    def get(self):
        body = request.args.to_dict()
        return Select(QMirroring, body).precise()


class RepoEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RepoEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "创建repo源",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RepoCreate
    })
    def post(self, body: RepoCreate):
        return Insert(Repo, body.__dict__).single(Repo, '/repo')

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RepoEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "删除repo源",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": DeleteBaseModel
    })
    def delete(self, body: DeleteBaseModel):
        return Delete(Repo, body.__dict__).batch(Repo, '/repo')

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RepoEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "修改repo源",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": RepoUpdate
    })
    def put(self, body: RepoUpdate):
        return Edit(Repo, body.__dict__).single(Repo, '/repo')

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_mirroring_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "RepoEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_mirroring_tag(),  # 当前接口所对应的标签
        "summary": "查询repo源",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(Repo)
    })
    def get(self):
        body = request.args.to_dict()
        return Select(Repo, body).fuzz()
