# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)相关接口的route层

import json

from celeryservice.tasks import resolve_testcase_file
from flask import request, g, jsonify, Response, send_file
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import or_

from server import redis_client, casbin_enforcer, swagger_adapt
from server.schema.base import QueryBaseModel
from server.utils.file_util import identify_file_type, FileTypeMapping, file_concurrency_lock
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect, workspace_error_collect
from server.utils.permission_utils import GetAllByPermission
from server.model.organization import Organization
from server.model.group import Group
from server.model.celerytask import CeleryTask
from server.model.testcase import Suite, Case, CaseNode, SuiteDocument, Baseline
from server.model.milestone import Milestone
from server.utils.db import Insert, Edit, Delete, collect_sql_error
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.schema.testcase import (
    CaseNodeBodySchema,
    CaseNodeQuerySchema,
    CaseNodeItemQuerySchema,
    CaseNodeSuitesCreateSchema,
    CaseNodeUpdateSchema,
    CasefileExportSchema,
    OrphanSuitesQuerySchema,
    SuiteCreate,
    CaseCreate,
    CaseCreateBody,
    CaseNodeCommitCreate,
    AddCaseCommitSchema,
    SuiteDocumentBodySchema,
    SuiteDocumentUpdateSchema,
    SuiteDocumentQuerySchema,
    BaselineCreateSchema,
    SuiteBaseUpdate,
    CaseCaseNodeUpdate,
    CaseNodeRelateSchema,
    ResourceQuerySchema,
    CaseSetQuerySchema,
    CaseSetNodeQueryBySuiteSchema,
    CaseQuery,
    SuiteQuery,
    CaseNodeBodyQuerySchema,
    CaseV2Query
)
from server.apps.testcase.handler import (
    CaseImportHandler,
    CaseNodeHandler,
    CaseHandler,
    ExcelExportUtil,
    MdExportUtil,
    OrphanSuitesHandler,
    TemplateCasesHandler,
    HandlerCaseReview,
    ResourceItemHandler,
    SuiteDocumentHandler,
    CaseSetHandler,
)
from server.utils.resource_utils import ResourceManager
from server.utils.page_util import PageUtil
from server import db


def get_testcase_tag():
    return {
        "name": "用例管理",
        "description": "用例管理相关接口",
    }


class CaseNodeEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "创建用例节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeBodySchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: CaseNodeBodySchema):
        return CaseNodeHandler.create(body)

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取用例根节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseNodeQuerySchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, workspace: str, query: CaseNodeQuerySchema):
        return CaseNodeHandler.get_roots(query, workspace)


class QueryCaseSetNodeEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "QueryCaseSetNodeEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "查询用例集节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseSetNodeQueryBySuiteSchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, query: CaseSetNodeQueryBySuiteSchema):
        return CaseNodeHandler.get_case_set_node(query)


class CaseNodeItemEvent(Resource):
    @auth.login_check
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "查询用例节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseSetNodeQueryBySuiteSchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, case_node_id: int, query: CaseNodeItemQuerySchema):
        return CaseNodeHandler.get(case_node_id, query)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "删除用例节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, case_node_id):
        return CaseNodeHandler.delete(case_node_id)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "修改用例节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeUpdateSchema
    })
    def put(self, case_node_id, body: CaseNodeUpdateSchema):
        return CaseNodeHandler.update(case_node_id, body)


class CaseNodeImportEvent(Resource):
    @auth.login_required()
    @casbin_enforcer.enforcer
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeImportEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "导入用例集",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                            "type": "object",
                            "properties": {
                                    "group_id": {
                                        "title": "用户组id",
                                        "type": "integer"
                                    },
                                    "file": {
                                        "type": "string",
                                        "format": "binary"}},
                            "required": ["file"]
                    }},
            }}
    })
    def post(self):
        file = request.files.get("file")
        if not file:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The file is must!"
            )
        with file_concurrency_lock("import_case_set", 2) as lock_info:
            if lock_info[0] is False:
                return lock_info[1]
            # 文件头检查
            verify_flag, res = identify_file_type(file, FileTypeMapping.case_set_type)
            if verify_flag is False:
                return res
            # 限制文件小于100M
            if file.content_length > 100 * 1024 * 1024:
                return jsonify(
                    error_code=RET.BAD_REQ_ERR,
                    error_msg="The file is too big!"
                )
            return CaseNodeHandler.import_case_set(
                file,
                request.form.get("group_id"),
            )

    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeImportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取所有用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""}  # 当前接口扩展文档定义
    })
    def get(self, case_node_id: int):
        return CaseNodeHandler.get_all_case(case_node_id)


class CaseNodeRelateItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeRelateItemEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "节点关联用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeRelateSchema
    })
    def post(self, case_node_id, body: CaseNodeRelateSchema):
        return CaseNodeHandler.relate(case_node_id, body)


class SuiteEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "测试套创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": SuiteCreate
    })
    def post(self, body: SuiteCreate):
        suite_body = body.__dict__

        suites = Suite.query.filter_by(name=suite_body["name"]).all()
        if suites:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The name of suite {} is already exist".format(
                    suite_body["name"]
                ),
            )

        suite_body.update({
            "source_type": "manual",
            "creator_id": g.user_id,
            "permission_type": "org",
            "org_id": redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        })
        _ = Insert(Suite, suite_body).insert_id(Suite, "/suite")
        return jsonify(error_code=RET.OK, error_msg="OK")

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "分页查询测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": SuiteQuery
    })
    def get(self, workspace: str, query: SuiteQuery):
        filter_params = GetAllByPermission(Suite, workspace, org_id=query.org_id).get_filter()

        if query.name is not None:
            filter_params.append(Suite.name.like(f'%{query.name}%'))
        if query.description is not None:
            filter_params.append(
                Suite.description.like(f'%{query.description}%'))
        if query.machine_type is not None:
            filter_params.append(Suite.machine_type == query.machine_type)
        if query.machine_num is not None:
            filter_params.append(Suite.machine_num == query.machine_num)
        if query.owner is not None:
            filter_params.append(Suite.owner == query.owner)
        if query.deleted is not None:
            filter_params.append(Suite.deleted.is_(query.deleted))
        if query.git_repo_id is not None:
            filter_params.append(Suite.git_repo_id == query.git_repo_id)
        query_filter = Suite.query.filter(*filter_params)

        return PageUtil.get_data(query_filter, query)


class OrphanOrgSuitesEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "OrphanOrgSuitesEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "分页查询组织下的孤儿测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": OrphanSuitesQuerySchema
    })
    def get(self, query: OrphanSuitesQuerySchema):
        handler = OrphanSuitesHandler(query)
        handler.add_filters([
            Suite.permission_type == "org",
        ])
        return handler.get_all()


class OrphanGroupSuitesEvent(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "OrphanGroupSuitesEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "分页查询用户组下的孤儿测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": OrphanSuitesQuerySchema
    })
    def get(self, group_id: int, query: OrphanSuitesQuerySchema):
        handler = OrphanSuitesHandler(query)
        handler.add_filters([
            Suite.group_id == group_id,
            Suite.permission_type == "group",
        ])
        return handler.get_all()


class CaseNodeSuitesEvent(Resource):
    @auth.login_required()
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeSuitesEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "测试套节点创建",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeSuitesCreateSchema
    })
    def post(self, case_node_id, body: CaseNodeSuitesCreateSchema):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node or not case_node.in_set:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"case node #{case_node_id} does not exist/not valid",
            )

        from celeryservice.tasks import async_create_testsuite_node
        for suite_id in body.suites:
            _task = async_create_testsuite_node.delay(
                case_node.id,
                suite_id,
                body.permission_type,
                body.org_id,
                body.group_id,
                g.user_id,
            )
            celerytask = {
                "tid": _task.task_id,
                "status": "PENDING",
                "object_type": "create_testsuite_node",
                "description": f"create case node related to suite#{suite_id} under {case_node.title}",
                "user_id": g.user_id,
            }

            _ = Insert(CeleryTask, celerytask).single(
                CeleryTask, "/celerytask")

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class SuiteItemEvent(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取测试套信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, suite_id):
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.OK,
                error_msg="The suite does not exist."
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=suite.to_json()
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "编辑测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": SuiteBaseUpdate
    })
    def put(self, suite_id, body: SuiteBaseUpdate):
        suite = Suite.query.filter_by(
            id=suite_id,
            source_type="manual",
        ).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the suite does not exist, or no right"
            )

        if body.name and body.name != suite.name:
            suites = Suite.query.filter_by(name=body.name).all()
            if suites:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The name of suite {} is already exist".format(
                        body.name
                    ),
                )

        _data = body.__dict__
        _data.update({"id": suite_id})
        Edit(Suite, body.__dict__).single(Suite, "/suite")
        return jsonify(error_code=RET.OK, error_msg="OK")

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "删除测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, suite_id):
        suite = Suite.query.filter(
            Suite.id == suite_id,
            or_(
                Suite.source_type == "manual",
                Suite.deleted.is_(True)
            )
        ).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="suite does not exist, or no right."
            )
        case_nodes = CaseNode.query.filter(
            CaseNode.suite_id == suite_id,
            CaseNode.type == "suite",
        ).all()

        source = list()
        for _case_node in case_nodes:
            cur = _case_node
            node_path = ""
            while cur:
                if not cur.parent.all():
                    node_path = cur.title + "->" + node_path
                    break
                if len(cur.parent.all()) > 1:
                    raise RuntimeError(
                        "case_node should not have parents beyond one")
                node_path = cur.title + "->" + node_path
                cur = cur.parent[0]
            source.append(node_path[:-2])
        if len(source) > 0:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"there are case nodes associated with suite {suite.name}",
                data=source
            )
        db.session.delete(suite)
        db.session.commit()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
        )


class PreciseSuiteEvent(Resource):
    @auth.login_required
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PreciseSuiteEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "精确获取测试套",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(Suite)
    })
    def get(self, workspace: str):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Suite, workspace).precise(body)


class PreciseCaseEvent(Resource):
    @auth.login_required
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "PreciseCaseEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "精确获取测试用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(Case)
    })
    def get(self, workspace: str):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Case, workspace).precise(body)


class CaseNodeCommitEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeCommitEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "用例节点提交",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeCommitCreate
    })
    def post(self, body: CaseNodeCommitCreate):
        return CaseHandler.create_case_node_commit(body)


class CaseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "创建用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseCreate
    })
    def post(self, body: CaseCreate):
        return_data = dict()
        case_body = body.__dict__
        _suite = Suite.query.filter_by(name=case_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The suite {} is not exist".format(
                    case_body.get("suite")
                )
            )
        case_body["suite_id"] = _suite.id
        case_body.pop("suite")

        case = Case.query.filter_by(name=case_body["name"]).first()
        if case:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="The name of case {} is already exist".format(
                    case_body["name"]
                ),
            )
        case_body.update({"creator_id": g.user_id})
        case_body.update({
            "org_id": redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        })

        _id = Insert(Case, case_body).insert_id(Case, "/case")
        return_data["case_id"] = _id

        case_body.update({"case_id": _id})
        case_node = CaseNode.query.filter_by(suite_id=_suite.id).first()
        if not case_node:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="case-node is not exist.")
        case_body.update({"parent_id": case_node.id})

        body = CaseCreateBody(**case_body)
        _resp = CaseNodeHandler.create(body)
        _resp = json.loads(_resp.data.decode('UTF-8'))
        if _resp.get("error_code") != RET.OK:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="Create case_node error."
            )
        return_data["case_node_id"] = _resp.get("data")
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "分页查询用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseQuery
    })
    def get(self, workspace: str, query: CaseQuery):
        filter_params = GetAllByPermission(Case, workspace, org_id=query.org_id).get_filter()

        if query.name is not None:
            filter_params.append(Case.name.like(f'%{query.name}%'))
        if query.description is not None:
            filter_params.append(
                Case.description.like(f'%{query.description}%'))
        if query.automatic is not None:
            filter_params.append(Case.automatic.is_(query.automatic))
        if query.test_level is not None:
            filter_params.append(Case.test_level == query.test_level)
        if query.test_type is not None:
            filter_params.append(Case.test_type == query.test_type)
        if query.machine_type is not None:
            filter_params.append(Case.machine_type == query.machine_type)
        if query.machine_num is not None:
            filter_params.append(Case.machine_num == query.machine_num)
        if query.owner is not None:
            filter_params.append(Case.owner == query.owner)
        if query.deleted is not None:
            filter_params.append(Case.deleted.is_(query.deleted))
        if query.suite_id is not None:
            filter_params.append(Case.suite_id == query.suite_id)
        query_filter = Case.query.filter(*filter_params)

        return PageUtil.get_data(query_filter, query)


class CaseItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "编辑用例节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseCaseNodeUpdate
    })
    def put(self, case_id, body: CaseCaseNodeUpdate):
        _body = body.__dict__
        _case = Case.query.filter_by(id=case_id).first()
        if not _case:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the case does not exist"
            )

        if body.name and body.name != _case.name:
            suites = Suite.query.filter_by(name=body.name).all()
            if suites:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The name of case {} is already exist".format(
                        body.name
                    ),
                )

        if _body["suite"]:
            _body["suite_id"] = Suite.query.filter_by(
                name=_body.get("suite")).first().id
            _body.pop("suite")
        _body['id'] = case_id
        Edit(Case, _body).single(Case, "/case")

        if body.name:
            case_nodes = CaseNode.query.filter(
                CaseNode.case_id == case_id,
            ).all()

            if not case_nodes:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="the case_node does not exist"
                )

            for case_node in case_nodes:
                if case_node.title != body.name:
                    case_node.title = body.name
                    case_node.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "删除用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, case_id):
        case_node = CaseNode.query.filter(
            CaseNode.case_id == case_id,
            CaseNode.type == "case",
            CaseNode.baseline_id.is_(None)
        ).first()
        if not case_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the case_node does not exist"
            )
        Delete(CaseNode, {"id": case_node.id}).single(CaseNode, "/case_node")
        return Delete(Case, {"id": case_id}).single(Case, "/case")

    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取用例信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, case_id):
        case = Case.query.filter_by(id=case_id).first()
        if not case:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK"
            )
        data = case.to_json()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )


class TemplateCasesQuery(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "TemplateCasesQuery",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "通过git_repo_id获取所有测试套及所有用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, git_repo_id):
        return TemplateCasesHandler.get_all(git_repo_id)


class CaseRecycleBin(Resource):
    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseRecycleBin",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "用例回收站数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryBaseModel

    })
    def get(self, workspace: str, query: QueryBaseModel):
        return GetAllByPermission(Case, workspace, org_id=query.org_id).precise({"deleted": 1})


class SuiteRecycleBin(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteRecycleBin",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "测试套回收站数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, workspace: str):
        return GetAllByPermission(Suite, workspace).precise({"deleted": 1})


class CaseImport(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseImport",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "用例导入",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {
                                "type": "string",
                                "format": "binary"}},
                        "required": ["file"]
                    }},
            }}
    })
    def post(self):
        if not request.files.get("file"):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The file being uploaded is not exist"
            )
        with file_concurrency_lock("import_test_case", 5) as lock_info:
            if lock_info[0] is False:
                return lock_info[1]
            try:

                file = request.files.get("file")
                # 文件头检查
                verify_flag, res = identify_file_type(file, FileTypeMapping.test_case_type)
                if verify_flag is False:
                    return res
                # 限制文件小于20M
                if file.content_length > 20 * 1024 * 1024:
                    return jsonify(
                        error_code=RET.BAD_REQ_ERR,
                        error_msg="The file is too big!"
                    )
                import_handler = CaseImportHandler(file)
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.RUNTIME_ERROR,
                    error_msg=str(e),
                )

            return import_handler.import_case(
                request.form.get("group_id"),
                request.form.get("case_node_id"),
            )


class ResolveTestcaseByFilepath(Resource):
    @auth.login_required()
    @response_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ResolveTestcaseByFilepath",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "给定文件路径解析测试用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "group_id": {
                                "type": "integer",
                                "title": "用户组id"},
                            "parent_id": {
                                "type": "integer",
                                "title": "上级id"},
                            "file": {
                                "type": "string",
                                "format": "binary"}},
                        "required": ["file"]
                    }},
            }}
    })
    def post(self):
        body = request.json

        permission_type = "org"
        if body.get("group_id"):
            permission_type = "group"

        _task = resolve_testcase_file.delay(
            body.get("filepath"),
            CeleryTaskUserInfoSchema(
                auth=request.headers.get("authorization"),
                user_id=g.user_id,
                group_id=body.get("group_id"),
                org_id=redis_client.hget(
                    RedisKey.user(g.user_id),
                    'current_org_id'
                ),
                permission_type=permission_type,
            ).__dict__,
            body.get("parent_id"),
        )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "tid": _task.task_id
            }
        )


class CaseCommit(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseCommit",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "用例修改提交",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": AddCaseCommitSchema
    })
    def post(self, body: AddCaseCommitSchema):
        """
        用例修改提交
        :return:
        """
        return HandlerCaseReview.create(body)


class CaseNodeTask(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeTask",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取节点任务",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, case_node_id):
        return CaseNodeHandler.get_task(case_node_id)


class MileStoneCaseNode(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "MileStoneCaseNode",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "通过milestone_id获取用例节点信息及进度",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, milestone_id):
        return CaseNodeHandler.get_case_node(milestone_id)


class ProductCaseNode(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ProductCaseNode",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "通过product_id获取用例节点信息及进度",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_id):
        return CaseNodeHandler.get_product_case_node(product_id)


class GroupNodeItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "GroupNodeItem",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取用户组下用例管理统计数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ResourceQuerySchema
    })
    def get(self, group_id, query: ResourceQuerySchema):
        try:
            return ResourceItemHandler(
                _type='group',
                group_id=group_id,
                commit_type=query.commit_type,
            ).run()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class OrgNodeItem(Resource):
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "OrgNodeItem",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取组织下用例管理统计数据",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ResourceQuerySchema
    })
    def get(self, org_id, query: ResourceQuerySchema):
        try:
            return ResourceItemHandler(
                _type='org',
                org_id=org_id,
                commit_type=query.commit_type,
            ).run()
        except RuntimeError as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )


class SuiteDocumentEvent(Resource):
    """
        创建、查询基线模板节点(Document).
        url="/api/v1/suite/<int:suite_id>/document"
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteDocumentEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "测试套添加文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": SuiteDocumentBodySchema
    })
    def post(self, suite_id, body: SuiteDocumentBodySchema):
        """
            在数据库中新增Document数据.
            请求体:
            {
                "url": str,
                "title": str,
            }
            返回体:
            {
                "data": {
                    "id": int
                },
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        return SuiteDocumentHandler.post(suite_id, body)

    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteDocumentEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取测试套文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": SuiteDocumentQuerySchema
    })
    def get(self, suite_id, query: SuiteDocumentQuerySchema):
        """
            在数据库中查询Document数据.
            api:/api/v1/suite/<int:suite_id>/document
            返回体:
            {
                "data": [
                    {
                        "case_node_id": int,
                        "creator_id": int,
                        "id": int,
                        "name": str,
                        "url": str
                    }
                ],
                "error_code": "2000",
                "error_msg": "OK!"
            }
        """
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The suite is not exist"
            )
        filter_params = GetAllByPermission(SuiteDocument).get_filter()
        filter_params.append(SuiteDocument.suite_id == suite_id)

        for key, value in query.dict().items():

            if not value:
                continue
            if key == 'title':
                filter_params.append(SuiteDocument.title.like(f'%{value}%'))
        suitedocuments = SuiteDocument.query.filter(*filter_params).all()
        return_data = [document.to_json() for document in suitedocuments]

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class SuiteDocumentItemEvent(Resource):
    """
        查询指定测试套文档.
        url="/api/v1/suite-document/<int:document_id>", 
        methods=["GET"]
    """
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteDocumentItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取指定测试套文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, document_id):
        """
            查询指定测试套文档..
            api:/api/v1/suite-document/<int:document_id>
            返回体:
            {
                "data": [
                    {
                        "case_node_id": int,
                        "creator_id": int,
                        "id": int,
                        "name": str,
                        "url": str
                    }
                ],
                "error_code": "2000",
                "error_msg": "OK!"
            }
        """
        return GetAllByPermission(SuiteDocument).precise({"id": document_id})

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteDocumentItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "修改指定测试套文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": SuiteDocumentUpdateSchema
    })
    def put(self, document_id, body: SuiteDocumentUpdateSchema):
        """
            修改指定测试套文档.
            api:/api/v1/suite-document/<int:document_id>
            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        _body = body.__dict__
        _body.update(
            {
                "id": document_id
            }
        )
        return Edit(SuiteDocument, _body).single(
            SuiteDocument, "/suite_document"
        )

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "SuiteDocumentItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "删除指定测试套文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, document_id):
        """
            删除指定测试套文档.
            api:/api/v1/suite-document/<int:document_id>
            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        document = SuiteDocument.query.filter_by(id=document_id).first()
        if not document:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The document {} is not exist".format(
                    document_id
                )
            )
        return ResourceManager("suite_document").del_single(document_id)


class CaseNodeDocumentsItemEvent(Resource):
    """
        查询case-node下的测试套文档.
        url="/api/v1/case-node/<int:case_node_id>/documents", 
        methods=["GET"]
    """
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeDocumentsItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "查询case-node下的测试套文档",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, case_node_id):
        """
            查询case-node下的测试套文档.
            api:/api/v1/case-node/<int:case_node_id>/documents
            返回体:
            {
                "data": [
                    {
                        "case_node_id": int,
                        "creator_id": int,
                        "id": int,
                        "name": str,
                        "url": str
                    }
                ],
                "error_code": "2000",
                "error_msg": "OK!"
            }
        """
        return GetAllByPermission(SuiteDocument).precise({
            "case_node_id": case_node_id
        })


class CaseNodeMoveToEvent(Resource):
    """
        修改指定用例节点的父信息.
        url="/api/v1/case-node/<int:from_id>/move-to/<int:to_id>", 
        methods=["PUT"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeMoveToEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "修改指定用例节点的父信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, from_id, to_id):
        """
            在数据库中修改指定用例节点的父信息.
            API:/api/v1/case-node/<int:from_id>/move-to/<int:to_id>
            返回体:
            {
            "error_code": "2000",
            "error_msg": "OK"
            }
        """
        from_casenode = CaseNode.query.filter_by(id=from_id).first()
        if not from_casenode:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The casenode is not exist."
            )
        old_parent = CaseNode.query.filter(
            CaseNode.children.contains(from_casenode)
        ).first()

        to_casenode = CaseNode.query.filter_by(id=to_id).first()
        if not to_casenode:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The casenode is not exist."
            )

        if from_id == to_id:
            return jsonify(error_code=RET.OK, error_msg="OK")

        if from_casenode.in_set == True and from_casenode.type == "case":
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Only suite and directory could be moved."
            )

        if to_casenode.type not in ["directory", "baseline"]:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Only could moved to type of directory or baseline."
            )

        from_casenode.parent.remove(old_parent)
        from_casenode.parent.append(to_casenode)
        from_casenode.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")


class CaseNodeGetRootEvent(Resource):
    """
        查询指定用例节点的根节点信息.
        url="/api/v1/case-node/<int:case_node_id>/get-root", 
        methods=["GET"]
    """
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseNodeGetRootEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "查询指定用例节点的根节点信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, case_node_id):
        """
            在数据库中查询指定用例节点的根节点信息.
            API:/api/v1/case-node/<int:case_node_id>/get-root
            返回体:
            {
            "baseline_id": int,
            "case_id": int,
            "group_id": int,
            "id": int,
            "in_set": bool,
            "is_root": bol,
            "org_id": int,
            "suite_id": int,
            "title": str,
            "type": str
            }
        """
        casenode = CaseNode.query.filter_by(id=case_node_id).first()
        if not casenode:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The casenode is not exist."
            )

        root_case_node = CaseNodeHandler.get_root_case_node(case_node_id)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=root_case_node.to_json()
        )


class CaseSetItemEvent(Resource):
    """
        查询baseline以及caseset的resource信息.
        url="/api/v1/case-node/<int:case_node_id>/resource", 
        methods=["GET"]
    """
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseSetItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "查询baseline或者caseset的resource信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseSetQuerySchema
    })
    def get(self, case_node_id, query: CaseSetQuerySchema):
        """
            在数据库中查询baseline或者caseset的resource信息.
            API: /api/v1/case-node/<int:case_node_id>/resource?commit_type=week
            返回体:
            {
            "auto_ratio": float,
            "case_count": int,
            "commit_attribute": {
            },
            "commit_count": int,
            "distribute": {
                "2022-12-07": int,
                "2022-12-08": int,
                "2022-12-09": int,
                "2022-12-10": int,
                "2022-12-11": int,
                "2022-12-12": int,
                "2022-12-13": int
            },
            "suite_count": int,
            "type_distribute": [
                {
                "name": str,
                "value": int
                },
                {
                "name": str,
                "value": int
                }
            ]
            }
        """
        return_data = dict()
        casenode = CaseNode.query.filter_by(id=case_node_id).first()
        if not casenode:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="casenode is not exist."
            )

        if casenode.type == "baseline" and casenode.is_root == True:
            # 获取基线baseline的details
            return_data = CaseSetHandler.get_caseset_details(
                casenode, "baseline", query)
            if isinstance(return_data, Response):
                return return_data
        elif casenode.type == "directory" and\
                casenode.is_root == 1 and \
                casenode.title == "用例集":
            # 获取用例集details
            return_data = CaseSetHandler.get_caseset_details(
                casenode, "directory", query)
            if isinstance(return_data, Response):
                return return_data
        else:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The type of casenode is invalid or casenode is not root node."
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data
        )


class BaselineEvent(Resource):
    """
        创建、查询基线(BaseLine).
        url="/api/v1/baseline", 
        methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "BaselineEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "创建基线(BaseLine)",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": CaseNodeBodySchema
    })
    def post(self, body: CaseNodeBodySchema):
        """
            在数据库中创建基线(BaseLine).
            请求体:
            {
            "title": str,
            "milestone_id": int,
            "type": str,
            "permission_type": str,
            "group_id": int
            }
            返回体:
            {
            "data": {
                "baseline_id": int,
                "case_node_id": int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }
        """
        return_data = dict()
        milestone = Milestone.query.filter_by(id=body.milestone_id).first()
        if not milestone:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="milestone is not exist."
            )
        _baseline = Baseline.query.filter_by(
            milestone_id=body.milestone_id).first()
        if _baseline:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="baseline associated with milestone has exist."
            )

        baseline_body = BaselineCreateSchema(**body.__dict__).dict()

        baseline_body.update({"creator_id": g.user_id})
        baseline_body.update({
            "org_id": redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        })
        _id = Insert(Baseline, baseline_body).insert_id(Baseline, "/baseline")
        return_data["baseline_id"] = _id

        body.baseline_id = _id
        _resp = CaseNodeHandler.create(body)
        _resp = json.loads(_resp.data.decode('UTF-8'))

        if _resp.get("error_code") != RET.OK:
            return _resp
        return_data["case_node_id"] = _resp.get("data")
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "BaselineEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "根据里程碑查询版本基线信息及其对应节点信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseNodeBodyQuerySchema
    })
    def get(self, query: CaseNodeBodyQuerySchema):
        _baseline = Baseline.query.filter_by(
            milestone_id=query.milestone_id).first()
        if not _baseline:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="baseline not exist!"
            )

        root_case_node = CaseNode.query.filter_by(is_root=True, baseline_id=_baseline.id,
                                                  milestone_id=_baseline.milestone_id).first()
        if not root_case_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="case node not exist!"
            )
        data = _baseline.to_json()
        # 追加版本基线根节点id

        data.update({"root_case_node_id": root_case_node.id})
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data,
        )


class OrgCasesetEvent(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "OrgCasesetEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取组织下的用例集",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, org_id):
        return CaseNodeHandler.get_caseset_children("org", Organization, org_id)


class GroupCasesetEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "GroupCasesetEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "获取用户组下的用例集",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, group_id):
        return CaseNodeHandler.get_caseset_children("group", Group, group_id)


class CasefileConvertEvent(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CasefileConvertEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "文本用例格式转换",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": {
            "description": "",
            "content": {
                "multipart/form-data": {
                    "schema": {
                            "type": "object",
                            "properties": {
                                    "to": {
                                        "title": "转换后的格式",
                                        "type": "string",
                                        "enum": ["md", "xlsx"]
                                    },
                                    "file": {
                                        "type": "string",
                                        "format": "binary"}},
                            "required": ["product", "build", "file"]
                    }},
            }}
    })
    def post(self):
        """
            文本用例格式转换，markdown <=> excel
            请求表单:
            {
                "file": binary,
                "to": "md" | "xlsx",
            }
            返回体:
            .md/.xlsx file attachment
            or
            {
                "error_code": str,
                "error_msg": str
            }
        """
        file = request.files.get("file")
        to = request.form.get("to")
        # 文件头检查
        verify_flag, res = identify_file_type(file, FileTypeMapping.test_case_type)
        if verify_flag is False:
            return res
        if file.headers.get("Content-Type") == "text/markdown" and to != "xlsx" or to != "md":
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="only supports md => xlsx or xlsx => md"
            )

        try:
            import_handler = CaseImportHandler(file)
            converted_filepath = import_handler.convert(to)
        except RuntimeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e)
            )

        return send_file(converted_filepath, as_attachment=True)


class OrgSuiteExportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "OrgSuiteExportEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "组织类型测试套下文本用例集体导出",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CasefileExportSchema
    })
    def get(self, org_id: int, case_node_id: int, query: CasefileExportSchema):
        """
            组织类型测试套下文本用例集体导出，markdown/excel格式
            请求表单:
            {
                "filetype": "md" | "xlsx",
            }
            返回体:
            .md/.xlsx file attachment
            or
            {
                "error_code": str,
                "error_msg": str
            }
        """
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node or case_node.type != 'suite':
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the CaseNode[{case_node_id}] to export is not valid",
            )

        suite = Suite.query.filter_by(id=case_node.suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"the Suite[{case_node.suite_id}] to export doest not exist"
            )

        cases = Case.query.filter_by(suite_id=suite.id).all()
        cases_data = [case_.to_json() for case_ in cases]

        exportor = None
        if query.filetype == 'xlsx':
            exportor = ExcelExportUtil(filename=suite.name, cases=cases_data)
        elif query.filetype == 'md':
            exportor = MdExportUtil(filename=suite.name, cases=cases_data)

        try:
            exportor.create_casefile()
            exportor.inject_data()
            return send_file(
                exportor.get_casefile(),
                as_attachment=True,
            )
        except Exception as e:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=str(e)
            )
        finally:
            exportor.rm_casefile()


class CaseEventV2(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_testcase_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "CaseEventV2",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_testcase_tag(),  # 当前接口所对应的标签
        "summary": "分页查询版本基线下的用例",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": CaseV2Query
    })
    def get(self, workspace: str, query: CaseV2Query):
        filter_params = GetAllByPermission(Case, workspace).get_filter()
        if query.name is not None:
            filter_params.append(Case.name.like(f'%{query.name}%'))
        if query.description is not None:
            filter_params.append(
                Case.description.like(f'%{query.description}%'))
        if query.automatic is not None:
            filter_params.append(Case.automatic.is_(query.automatic))
        if query.baseline_id is not None:
            filter_params.append(CaseNode.baseline_id == query.baseline_id)
        query_filter = Case.query.join(CaseNode).filter(*filter_params)

        return PageUtil.get_data(query_filter, query)
