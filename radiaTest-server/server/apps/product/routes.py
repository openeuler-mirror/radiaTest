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

from flask.json import jsonify
from flask import request
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import case as sql_case

from server.model import Product, Milestone, TestReport
from server.utils.auth_util import auth
from server.utils.db import Edit, Select
from server.utils.page_util import PageUtil

from server.schema.product import ProductBase, ProductUpdate, ProductQueryBase
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server import casbin_enforcer, swagger_adapt
from server.utils.response_util import RET, response_collect, workspace_error_collect


def get_product_tag():
    return {
        "name": "产品",
        "description": "产品相关接口",
    }


class ProductEventItem(Resource):
    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductEventItem",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "删除产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, product_id):
        return ResourceManager("product").del_cascade_single(
            product_id, Milestone, [Milestone.product_id == product_id], False
        )

    @validate()
    @casbin_enforcer.enforcer
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductEventItem",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "获取产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_id):
        return Select(Product, {"id": product_id}).single()

    @auth.login_required
    @validate()
    @casbin_enforcer.enforcer
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductEventItem",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "编辑产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ProductUpdate
    })
    def put(self, product_id, body: ProductUpdate):
        product = Product.query.filter_by(id=product_id).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="edit product failed due to product does not exist.",
            )
        name = product.name
        version = product.version
        if body.name:
            name = body.name
        if body.version:
            version = body.version

        product = Product.query.filter_by(
            name=name, version=version
        ).first()
        if product and product.id != product_id:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="edit product failed due to the version of product has existed.",
            )
        _data = body.__dict__
        _data["id"] = product_id
        Edit(Product, _data).single(Product, '/product')
        return jsonify(
            error_code=RET.OK,
            error_msg=f"edit product[{product_id}] success",
        )


class ProductEvent(Resource):
    @auth.login_required
    @validate()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "注册产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": ProductBase
    })
    def post(self, body: ProductBase):
        return ResourceManager("product").add("api_infos.yaml", body.__dict__)

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "分页查询产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": ProductQueryBase
    })
    def get(self, workspace: str, query: ProductQueryBase):
        _g = GetAllByPermission(Product, workspace, org_id=query.org_id)
        if query.permission_type is not None:
            _g.set_filter(Product.permission_type == query.permission_type)
            ords = [Product.name.asc(), Product.create_time.asc()]
        else:
            _ord = sql_case(
                (Product.permission_type == 'org', 1),
                (Product.permission_type == 'public', 2),
                (Product.permission_type == 'group', 3),
                (Product.permission_type == 'person', 4)
            )
            ords = [_ord, Product.name.asc(), Product.create_time.asc()]
        query_filter = _g.fuzz(
            query.__dict__,
            ords,
            "query"
        )
        return PageUtil.get_data(query_filter, query)


class PreciseProductEvent(Resource):
    @auth.login_required
    @response_collect
    @workspace_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "PreciseProductEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "精确查询产品",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": swagger_adapt.get_query_schema_by_db_model(Product)
    })
    def get(self, workspace: str):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Product, workspace).precise(body)


class UpdateProductIssueRate(Resource):
    @auth.login_required
    @validate()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "UpdateProductIssueRate",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "同步当前版本所有issue比率",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def put(self, product_id):
        from celeryservice.tasks import async_update_all_issue_rate
        product = Product.query.filter_by(id=product_id, is_forced_check=True).first()
        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product does not exist.",
            )

        async_update_all_issue_rate.delay(product_id)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class ProductTestReportEvent(Resource):
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_product_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "ProductTestReportEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_product_tag(),  # 当前接口所对应的标签
        "summary": "获取当前产品的测试报告",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_id):
        _product = Product.query.filter_by(id=product_id).first()
        if not _product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="product doesn't exist.",
            )

        _test_reports = TestReport.query.join(Milestone).filter(
            TestReport.milestone_id == Milestone.id,
            Milestone.product_id == product_id
        ).all()
        data = []
        if _test_reports:
            data = [tr.to_json() for tr in _test_reports]

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )
