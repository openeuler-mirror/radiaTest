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
# Date : 2023/3/13 14:00:00
# License : Mulan PSL v2
#####################################
# 测试策略(Strategy)相关接口的route层

import json

from flask import g, jsonify, current_app, request
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import not_

from server import redis_client, db, swagger_adapt
from server.utils.page_util import PageUtil
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.file_util import FileUtil
from server.utils.response_util import RET, response_collect
from server.model.product import Product
from server.model.qualityboard import Feature
from server.model.strategy import ReProductFeature, Strategy, StrategyTemplate, StrategyCommit
from server.utils.db import Insert, Edit, Delete, Precise, collect_sql_error
from server.schema.strategy import (
    FeatureQuerySchema,
    FeatureSetBodySchema,
    FeatureSetUpdateSchema,
    StrategyTemplateBodySchema,
    StrategyTemplateQuerySchema,
    StrategyBodySchema,
    StrategyRelateSchema,
    StrategyCommitBodySchema,
    StrategyCommitUpdateSchema,
    StrategyQuerySchema,
    StrategyPermissionBaseSchema,
)
from server.apps.strategy.handler import (
    FeatureHandler,
    InheritFeatureHandler,
    CommitHandler,
)
from server.utils.response_util import value_error_collect


def get_strategy_tag():
    return {
        "name": "测试策略",
        "description": "测试策略相关接口",
    }


class FeatureSetEvent(Resource):
    """
        创建特性
        url="/api/v1/feature", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSetEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "创建特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": FeatureSetBodySchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, body: FeatureSetBodySchema):
        """
            在数据库中Feature表中创建特性.
            API: "/api/v1/feature"
            请求体:
            {
                "feature": str,
                "no": str,
                "owner": long text,
                "pkgs": long text,
                "release_to": str,
                "sig": str,
                "status": str,
                "url": str
            }

            返回体:
            {
                "data": {
                    "id": int,
                },
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        _body = body.__dict__
        _body.update({
            "status": "Accepted",
            "sig": ",".join(body.sig),
            "owner": ",".join(body.owner),
        })
        filter_params = [
            Feature.feature == _body.get("feature"),
            Feature.sig == _body.get("sig"),
            Feature.owner == _body.get("owner")
        ]
        feature_id = FeatureHandler(filter_params, True, _body).create_node()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={'id': feature_id}
        )

    """
        获取特性集
        url="/api/v1/feature", 
        methods=["Get"]
    """

    @auth.login_check
    @response_collect
    @value_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSetEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "分页查询特性集",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": StrategyQuerySchema,  # 当前接口请求体参数schema校验器
    })
    def get(self, query: StrategyQuerySchema):
        """
            在数据库中查询特性集.
            API: "/api/v1/feature"

            返回体:
            {
                "data": [
                    {
                        "feature": str,
                        "id": int,
                        "no": str,
                        "owner": long text,
                        "pkgs": long text,
                        "product_feature_id": int,
                        "product_id": int,
                        "release_to": str,
                        "sig": str,
                        "status": str,
                        "task_status": str,
                        "url": str
                    }
                ],
                "error_code": "2000",
                "error_msg": "OK"
            } 
        """
        if query.type:
            new_feature = ReProductFeature.query.filter_by(is_new=1).all()
            new_feature_ids = [feature.feature_id for feature in new_feature]
            features = db.session.query(Feature).filter(not_(Feature.id.in_(set(new_feature_ids)))).all()
            _data = [feature.to_json() for feature in features]
        else:
            features = db.session.query(Feature)
            return PageUtil.get_data(features, query)

        return jsonify(
            data=_data,
            error_code=RET.OK,
            error_msg="OK"
        )


class StrategyRelateEvent(Resource):
    """
        关联继承特性
        url="/api/v1/product/<int:product_id>/relate", 
        methods=["Post"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyRelateEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "关联继承特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyRelateSchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, product_id, body: StrategyRelateSchema):
        """
            在数据库中关联继承特性.
            API: "/api/v1/product/<int:product_id>/relate"
            请求体:
            {
                "feature_id": int,
                "is_new": bool
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
        re_feature = ReProductFeature.query.filter_by(product_id=product_id, feature_id=body.feature_id).first()
        if re_feature:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The product has related this feature"
            )

        re_product_feature_id = InheritFeatureHandler.create_relate_data(body, product_id)

        return jsonify(
            data={"id": re_product_feature_id},
            error_code=RET.OK,
            error_msg="OK"
        )


class FeatureSetItemEvent(Resource):
    """
        获取某个特性
        url="/api/v1/feature/<int:feature_id>", 
        methods=["Get"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSetItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "特性详情",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, feature_id):
        """
            在数据库中查询指定特性. 
            API: "/api/v1/feature/<int:feature_id>"

            返回体:
            {
                "data": {
                    "feature": str,
                    "id": int,
                    "is_new": bool,
                    "no": str,
                    "owner": long text,
                    "pkgs": long text,
                    "release_to": str,
                    "sig": str,
                    "status": str,
                    "task_status": str,
                    "url": str
                },
                "error_code": "2000",
                "error_msg": "OK"
            } 
        """
        feature = FeatureHandler(
            body={"id": feature_id}
        ).get_node()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=feature.to_json()
        )

    """
        修改指定特性
        url="/api/v1/feature/<int:feature_id>", 
        methods=["Put"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSetItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "修改指定特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": FeatureSetUpdateSchema
    })
    def put(self, feature_id, body: FeatureSetUpdateSchema):
        """
            在数据库中修改指定特性.
            API: "/api/v1/feature/<int:feature_id>"
            请求体:
            {
                "feature": str,
                "is_new": bool,
                "no": str,
                "owner": long text,
                "pkgs": long text,
                "release_to": str,
                "sig": str,
                "status": str,
                "url": str
            }

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }   
        """
        data = body.__dict__
        data.update({
            "id": feature_id
        })
        if body.feature:
            feature = Feature.query.filter_by(id=feature_id).first()
            feature_put = Feature.query.filter_by(feature=body.feature).first()
            if feature_put and feature != feature_put:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The title of feature is exist, Please modify."
                )

            FeatureHandler(
                body=data
            ).put_node(feature)
            return jsonify(
                error_code=RET.OK,
                error_msg="update feature success"
            )
        else:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="feature can't be none"
            )

    """
        删除指定特性
        url="/api/v1/feature/<int:feature_id>", 
        methods=["Delete"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "FeatureSetItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "删除指定特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, feature_id):
        """
            在数据库中删除指定特性.
            API: "/api/v1/feature/<int:feature_id>"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            } 
        """
        FeatureHandler(
            body={"id": feature_id}
        ).delete_node()
        return jsonify(
            error_code=RET.OK,
            error_msg="delete feature success"
        )


class ProductFeatureEvent(Resource):
    """
        查询指定产品下所有特性，包括新特性以及继承特性(Feature).
        url="/api/v1/product/<int:product_id>/feature", methods=["GET"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ProductFeatureEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "获取产品所有特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": FeatureQuerySchema
    })
    def get(self, product_id, query: FeatureQuerySchema):
        """
            在数据库查询产品所有特性，包括新特性以及继承特性.
            返回体:
            {
                "data": [
                    {
                        "feature": str,
                        "is_new": bool,
                        "no": str,
                        "owner": long text,
                        "pkgs": long text,
                        "release_to": str,
                        "sig": str,
                        "status": str,
                        "url": str
                    },
                ]
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        return_data = list()

        filter_params = [
            ReProductFeature.product_id == product_id,
            Feature.id == ReProductFeature.feature_id,
            ReProductFeature.is_new == query.is_new
        ]

        product_features = db.session.query(ReProductFeature, Feature).filter(*filter_params).all()
        if not product_features:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK"
            )

        for p_f, feature in product_features:
            _feature_data = {
                **p_f.to_json(),
                **feature.to_json(),
            }
            return_data.append(_feature_data)

            strategy_commit = db.session.query(StrategyCommit, Strategy).filter(
                p_f.id == Strategy.product_feature_id,
                Strategy.id == StrategyCommit.strategy_id,
            ).first()

            if not strategy_commit:
                continue
            _feature_data.update(
                **strategy_commit[0].to_combine_json()
            )

        return jsonify(
            data=return_data,
            error_code=RET.OK,
            error_msg="OK"
        )


class StrategyCommitEvent(Resource):
    """
        获取测试策略脑图
        url="/api/v1/product-feature/<int:product_feature_id>/strategy", 
        methods=["Get"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "获取测试策略脑图",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_feature_id):
        """
            在数据库中查询测试策略脑图.
            API: "/api/v1/product-feature/<int:product_feature_id>/strategy"

            返回体:
            {
                "data": {
                    "id": int
                    "org_id": int,
                    "product_feature_id": int,
                    "tree": longtext
                },
                "error_code": "2000",
                "error_msg": "OK"
            } 
        """
        product_feature = ReProductFeature.query.filter_by(
            id=product_feature_id
        ).first()
        if not product_feature:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The no. of re_product_feature {} is not exist".format(
                    product_feature_id
                )
            )

        strategy = Strategy.query.filter_by(
            product_feature_id=product_feature_id
        ).first()
        if not strategy:
            return jsonify(
                error_code=RET.OK,
                error_msg="The strategy is not exist."
            )

        strategy_commit = db.session.query(StrategyCommit, Strategy).filter(
            product_feature_id == Strategy.product_feature_id,
            Strategy.id == StrategyCommit.strategy_id,
        ).first()

        if strategy_commit:
            return jsonify(
                data=strategy_commit[0].to_json(),
                error_code=RET.OK,
                error_msg="OK"
            )
        else:
            strategy = Strategy.query.filter_by(id=strategy.id).first()
            return jsonify(
                data=strategy.to_json(),
                error_code=RET.OK,
                error_msg="OK"
            )

    """
        创建测试策略
        url="/api/v1/product-feature/<int:product_feature_id>/strategy", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "创建测试策略",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyBodySchema
    })
    def post(self, product_feature_id, body: StrategyBodySchema):
        """
            在数据库中创建测试策略.
            API: "/api/v1/product-feature/<int:product_feature_id>/strategy"
            请求体:
            {
                "org_id": int,
                "product_feature_id": int,
                "tree": dict,
                "file_type": "str
            }

            返回体:
            {
            "data": {
                id: int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        feature = Feature.query.join(ReProductFeature).filter(
            ReProductFeature.id == product_feature_id,
            ReProductFeature.feature_id == Feature.id
        ).first()

        if not feature:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="feature is not exists"
            )

        strategy_commit = db.session.query(StrategyCommit).filter(
            Strategy.product_feature_id == product_feature_id,
            StrategyCommit.strategy_id == Strategy.id
        ).first()
        if strategy_commit:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="strategy commit is not empty"
            )

        strategy_record = Strategy()
        strategy_record.product_feature_id = product_feature_id
        strategy_record.file_type = "New"
        strategy_record.tree = json.dumps(
            {"data": {
                "text": feature.feature + "测试策略",
                "id": 0
            }}
        )
        strategy_record.creator_id = g.user_id
        strategy_record.org_id = redis_client.hget(
            RedisKey.user(g.user_id),
            "current_org_id"
        )

        db.session.add(strategy_record)
        db.session.flush()

        strategy_commit_record = StrategyCommit()
        strategy_commit_record.strategy_id = strategy_record.id
        strategy_commit_record.commit_status = "staged"
        text = body.tree.get("data").get("text") + "测试策略"
        body.tree.get("data").update({"text": text})
        strategy_commit_record.commit_tree = json.dumps(body.tree)
        db.session.add(strategy_commit_record)
        db.session.flush()

        db.session.commit()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={"id": strategy_commit_record.id}
        )

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "删除产品测试策略",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": StrategyPermissionBaseSchema
    })
    def delete(self, product_feature_id, body: StrategyPermissionBaseSchema):
        strategy = Strategy.query.filter_by(
            org_id=body.org_id, creator_id=body.user_id, product_feature_id=product_feature_id
        ).first()
        if not strategy:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="you have no permission delete strategy or strategy has been delete"
            )

        db.session.delete(strategy)
        db.session.commit()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


class StrategyItemEvent(Resource):
    """
        获取测试策略
        url="/api/v1/strategy/<int:strategy_id>", 
        methods=["Get"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "获取测试策略",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, strategy_id):
        """
            在数据库中获取测试策略.
            API: "/api/v1/strategy/<int:strategy_id>"

            返回体:
            {
                "data": {
                    "org_id": int,
                    "product_feature_id": int,
                    "tree": dict,
                    "file_type": "str
                },
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        strategy = Strategy.query.filter_by(id=strategy_id).first()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=strategy.to_json()
        )

    """
        删除测试策略
        url="/api/v1/strategy/<int:strategy_id>", 
        methods=["Delete"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "删除测试策略",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, strategy_id):
        """
            在数据库中删除测试策略.
            API: "/api/v1/strategy/<int:strategy_id>"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }   
        """
        filter_params = [
            StrategyCommit.strategy_id == strategy_id,
            StrategyCommit.strategy_id == Strategy.id
        ]

        strategy_commit = db.session.query(Strategy, StrategyCommit).filter(*filter_params).first()
        if strategy_commit:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="Cannot be deleted because there is strategy-commit data."
            )

        strategy = Strategy.query.filter_by(id=strategy_id).first()
        if strategy:
            db.session.delete(strategy)
            db.session.commit()

        return jsonify(
            error_code=RET.OK,
            error_msg="delete strategy success"
        )


class StrategyTemplateEvent(Resource):
    """
        获取测试策略模板
        url="/api/v1/strategy-template", 
        methods=["Get"]
    """

    @auth.login_check
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "查询测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": StrategyTemplateQuerySchema
    })
    def get(self, query: StrategyTemplateQuerySchema):
        """
            在数据库中查询测试策略模板.
            API: "/api/v1/strategy-template"

            返回体:
            {
                "data": {
                    "id": 1,
                    "org_id": 5,
                    "title": "test_strategy_001",
                    "tree": "{\"title\": \"123\"}"
                },
                "error_code": "2000",
                "error_msg": "OK"
            }  
        """
        if query.title:
            strategy_templates = StrategyTemplate.query.filter(StrategyTemplate.title.like(f"%{query.title}%")).all()
        else:
            strategy_templates = StrategyTemplate.query.all()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[item.to_json() for item in strategy_templates]
        )

    """
        创建测试策略模板
        url="/api/v1/strategy-template", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "创建测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyTemplateBodySchema
    })
    def post(self, body: StrategyTemplateBodySchema):
        """
            在数据库中创建测试策略模板.
            API: "/api/v1/strategy-template"
            请求体：
            {
                "title": str,
                "tree": longtext
            }

            返回体:
            {
            "data": {id: int},
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        _body = body.__dict__
        strategy_template = StrategyTemplate.query.filter_by(title=_body.get("title")).first()
        if strategy_template:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="template name is already exists",
            )
        creator_id = g.user_id
        org_id = redis_client.hget(
            RedisKey.user(g.user_id),
            "current_org_id"
        )

        _body.update({
            "tree": json.dumps(body.tree),
            "creator_id": creator_id,
            "org_id": org_id
        })

        strategy_template_id = Insert(StrategyTemplate, _body).insert_id()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={"id": strategy_template_id}
        )


class StrategyTemplateItemEvent(Resource):
    """
        获取测试策略模板
        url="/api/v1/strategy-template/<int:strategy_template_id>", 
        methods=["Get"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "获取测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, strategy_template_id):
        """
            在数据库中查询测试策略模板.
            API: "/api/v1/strategy-template/<int:strategy_template_id>"

            返回体:
            {
                "data": {
                    "id": int,
                    "org_id": int,
                    "title": str,
                    "tree": longtext
                },
                "error_code": "2000",
                "error_msg": "OK"
            } 
        """
        strategy_template = StrategyTemplate.query.filter_by(id=strategy_template_id).first()
        if not strategy_template:
            data = {}
        else:
            data = strategy_template.to_json()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )

    """
        修改测试策略模板
        url="/api/v1/strategy-template/<int:strategy_template_id>", 
        methods=["Put"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "修改测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyTemplateBodySchema
    })
    def put(self, strategy_template_id, body: StrategyTemplateBodySchema):
        """
            在数据库中修改测试策略模板.
            API: "/api/v1/strategy-template/<int:strategy_template_id>"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            } 
        """
        _body = body.__dict__
        _body.update({
            "id": strategy_template_id,
            "tree": json.dumps(body.tree)
        })

        Edit(StrategyTemplate, _body).single(StrategyTemplate, "/strategytemplate")
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    """
        删除测试策略模板
        url="/api/v1/strategy-template/<int:strategy_template_id>", 
        methods=["Delete"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "删除测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, strategy_template_id):
        """
            在数据库中删除测试策略模板.
            API: "/api/v1/strategy-template/<int:strategy_template_id>"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }  
        """
        strategy_template = StrategyTemplate.query.filter_by(id=strategy_template_id).first()
        if strategy_template:
            db.session.delete(strategy_template)
            db.session.commit()

        return jsonify(
            error_code=RET.OK,
            error_msg="delete strategy template success"
        )


class StrategyTemplateApplyEvent(Resource):
    """
        应用测试策略模板
        url=""/api/v1/strategy-template/<int:strategy_template_id>/apply/strategy/<int:product_feature_id>", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyTemplateApplyEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "应用测试策略模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, strategy_template_id, product_feature_id):
        """
            在数据库中应用测试策略模板.
            API: ""/api/v1/strategy-template/<int:strategy_template_id>/apply/strategy/<int:product_feature_id>"
            返回体:
            {
            "data": {
                id: int,
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        strategy = Strategy.query.filter_by(product_feature_id=product_feature_id).first()
        if strategy:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="The strategy is already exist."
            )
        strategy_commit = db.session.query(StrategyCommit).filter(
            Strategy.product_feature_id == product_feature_id,
            StrategyCommit.strategy_id == Strategy.id
        ).first()

        if strategy_commit:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="The strategy commit is exist."
            )

        feature = Feature.query.join(ReProductFeature).filter(
            ReProductFeature.id == product_feature_id,
            ReProductFeature.feature_id == Feature.id
        ).first()

        if not feature:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="feature is not exist."
            )

        s_t = StrategyTemplate.query.filter_by(
            id=strategy_template_id
        ).first()
        if not s_t:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The strategy template is not exist."
            )

        strategy_record = Strategy()
        strategy_record.product_feature_id = product_feature_id
        strategy_record.file_type = "New"
        strategy_record.tree = json.dumps(
            {"data": {
                "text": feature.feature,
                "id": 0
            }}
        )
        strategy_record.creator_id = g.user_id
        strategy_record.org_id = redis_client.hget(
            RedisKey.user(g.user_id),
            "current_org_id"
        )

        db.session.add(strategy_record)
        db.session.flush()

        strategy_commit_record = StrategyCommit()
        strategy_commit_record.strategy_id = strategy_record.id
        strategy_commit_record.commit_status = "staged"
        strategy_commit_record.commit_tree = s_t.tree
        db.session.add(strategy_commit_record)
        db.session.flush()

        db.session.commit()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={"id": strategy_commit_record.id}
        )


class StrategyImportEvent(Resource):
    """
        暂存测试策略commit
        url="/api/v1/product-feature/<int:product_feature_id>/import", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    def post(self, product_feature_id):
        """
            暂存在数据库中创建测试策略commit.
            API: "/api/v1/product-feature/<int:product_feature_id>/import"
            请求体:
            {
                "commit_status": str,
                "commit_tree": dict,
            }

            返回体:
            {
            "data": {
                id: int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        # 二进制 md
        # md dict
        #

        pass


class StrategyExportEvent(Resource):
    """
        暂存测试策略commit
        url="/api/v1/product-feature/<int:product_feature_id>/import", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    def post(self, product_feature_id):
        """
            暂存在数据库中创建测试策略commit.
            API: "/api/v1/product-feature/<int:product_feature_id>/import"
            请求体:
            {
                "commit_status": str,
                "commit_tree": dict,
            }

            返回体:
            {
            "data": {
                id: int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        pass


class StrategySubmmitEvent(Resource):
    """
        暂存测试策略commit
        url="/api/v1/strategy/<int:strategy_id>/submmit", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategySubmmitEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "测试策略提交",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, strategy_id):
        """
            暂存在数据库中创建测试策略commit.
            API: "/api/v1/strategy/<int:strategy_id>/submmit"
            请求体:
            {
                "commit_status": str,
                "commit_tree": dict,
            }

            返回体:
            {
            "data": {
                id: int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """

        strategy_commit_info = db.session.query(Strategy, StrategyCommit).filter(
            StrategyCommit.strategy_id == strategy_id,
            StrategyCommit.strategy_id == Strategy.id,
            Strategy.creator_id == g.user_id,
            StrategyCommit.commit_status == "staged"
        ).first()
        if not strategy_commit_info:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="strategy commint is not exists"
            )

        strategy_commit = strategy_commit_info[1]
        try:
            handler = CommitHandler(strategy_id)
            handler.create_fork()

            handler.create_branch()

            md_content = strategy_commit.commit_tree
            handler.git_operate(md_content)
            strategy_commit.commit_status = "submitted"
            strategy_commit.add_update()
        except (RuntimeError, ValueError, TypeError) as e:
            strategy_commit.commit_status = "staged"
            strategy_commit.add_update()
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e)
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


class StrategyCommitStageEvent(Resource):
    """
        暂存测试策略commit
        url="/api/v1/strategy/<int:strategy_id>/strategy-commit/stage", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitStageEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "创建测试策略commit",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyCommitBodySchema
    })
    def post(self, strategy_id, body: StrategyCommitBodySchema):
        """
            暂存在数据库中创建测试策略commit.
            API: "/api/v1/strategy/<int:strategy_id>/strategy-commit/stage"
            请求体:
            {
                "commit_status": str,
                "commit_tree": dict,
            }

            返回体:
            {
            "data": {
                id: int
            },
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """
        _body = body.__dict__
        _body.update({
            "strategy_id": strategy_id,
            "commit_tree": json.dumps(body.commit_tree)
        })

        strategy_commit_info = db.session.query(Strategy, StrategyCommit).filter(
            StrategyCommit.strategy_id == strategy_id,
            StrategyCommit.strategy_id == Strategy.id,
            Strategy.creator_id == g.user_id,
            StrategyCommit.commit_status == "staged"
        ).first()

        if strategy_commit_info:
            strategy_commit = strategy_commit_info[1]
            _body.update({
                "id": strategy_commit.id
            })
            Edit(StrategyCommit, _body).single(StrategyCommit, "/strategycommit")
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={"id": strategy_commit.id}
            )
        else:
            strategy_commit_id = Insert(StrategyCommit, _body).insert_id()
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data={"id": strategy_commit_id}
            )


class StrategyCommitItemEvent(Resource):
    """
        获取测试策略commit
        url="/api/v1/product-feature/<int:product_feature_id>/strategy-commit", 
        methods=["Get"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitItemEvent",  # 当前接口视图函数名
        "func_name": "get",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "获取测试策略commit",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, product_feature_id):
        """
            在数据库中获取测试策略commit.
            API: "/api/v1/product-feature/<int:product_feature_id>/strategy-commit"

            返回体:
            {
                "data": {
                    "commit_status": str,
                    "commit_tree": dict,
                    "id": int,
                    "org_id": int,
                    "strategy_id": int
                },
                },
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        strategy = Strategy.query.filter_by(product_feature_id=product_feature_id).first()
        if not strategy:
            return jsonify(
                error_code=RET.OK,
                error_msg="The strategy is not exist."
            )

        strategy_commit = StrategyCommit.query.filter_by(strategy_id=strategy.id).first()
        if not strategy_commit:
            data = {}
        else:
            data = strategy_commit.to_json()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data
        )

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitItemEvent",  # 当前接口视图函数名
        "func_name": "put",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "编辑测试策略commit",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": StrategyCommitUpdateSchema
    })
    def put(self, strategy_commit_id, body: StrategyCommitUpdateSchema):
        """
            在数据库中获取测试策略commit.
            API: "/api/v1/product-feature/<int:product_feature_id>/strategy-commit"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }  
        """
        _body = body.__dict__
        _body.update({
            **_body,
            "id": strategy_commit_id,
            "commit_tree": json.dumps(body.commit_tree)
        })
        return Edit(StrategyCommit, _body).single(StrategyCommit, "/strategycommit")


class StrategyCommitReductEvent(Resource):
    """
        还原测试策略commit
        url="/api/v1/strategy/<int:strategy_id>/reduct", 
        methods=["Delete"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @collect_sql_error
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "StrategyCommitReductEvent",  # 当前接口视图函数名
        "func_name": "delete",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "删除测试策略commit",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, strategy_id):
        """
            在数据库中还原测试策略commit.
            API: "/api/v1/strategy/<int:strategy_id>/reduct"

            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }   
        """
        strategy_commit_info = db.session.query(Strategy, StrategyCommit).filter(
            StrategyCommit.strategy_id == strategy_id,
            StrategyCommit.strategy_id == Strategy.id,
            Strategy.creator_id == g.user_id,
            StrategyCommit.commit_status == "staged"
        ).first()

        if not strategy_commit_info:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The strategy_commit is not exist."
            )

        strategy_commit = strategy_commit_info[1]
        db.session.delete(strategy_commit)
        db.session.commit()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


class ProductInheritFeatureEvent(Resource):
    """
        更新继承特性
        url="/api/v1/product/<int:product_id>/inherit-feature", 
        methods=["POST"]
    """

    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_strategy_tag.__module__,   # 获取当前接口所在模块
        "resource_name": "ProductInheritFeatureEvent",  # 当前接口视图函数名
        "func_name": "post",   # 当前接口所对应的函数名
        "tag": get_strategy_tag(),  # 当前接口所对应的标签
        "summary": "更新继承特性",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, product_id):
        """
            在数据库中更新继承特性.
            API: "/api/v1/product/<int:product_id>/inherit-feature"

            返回体:
            {
                "data": {list},
                "error_code": "2000",
                "error_msg": "OK"
            } 
        """
        p = Product.query.filter_by(id=product_id).first()
        product = Product.query.filter(
            Product.create_time < p.create_time,

        ).order_by(
            Product.create_time.desc(),
        ).first()

        if not product:
            return jsonify(
                error_code=RET.OK,
                error_msg="The older product is not exist."
            )

        fs, _data = list(), list()
        fs = InheritFeatureHandler().get_inherit_feature(product)
        for item in fs:
            _data.append(item.id)
        return jsonify(
            data=_data,
            error_code=RET.OK,
            error_msg="OK"
        )
