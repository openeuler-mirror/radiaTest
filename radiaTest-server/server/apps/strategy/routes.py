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
# Date : 2023/3/20 14:00:00
# License : Mulan PSL v2
#####################################
# 测试策略(Strategy)相关接口的route层

import json
import os

from flask import request, g, jsonify, current_app, Response, send_from_directory
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import or_, and_, func
from server import redis_client, casbin_enforcer, db
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.file_util import FileUtil
from server.utils.response_util import RET, response_collect
from server.utils.permission_utils import GetAllByPermission
from server.model.product import Product
from server.model.qualityboard import Feature
from server.model.testcase import CaseNode, Suite, Case
from server.model.strategy import ReProductFeature, Strategy, StrategyTemplate, StrategyCommit
from server.utils.db import Insert, Edit, Delete, Precise, collect_sql_error
from server.schema.base import PageBaseSchema
from server.apps.testcase.routes import SuiteEvent, CaseEvent, CaseNodeEvent
from server.schema.testcase import CaseNodeItemQuerySchema, SuiteCreate
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
    CommitBodySchema,

)
from server.apps.strategy.handler import (
    ProductFeatureHandler,
    StrategyHandler,
    NodeHandler,
    InheritFeatureHandler,
    StrategyEventHandler,
    CommitHandler,
)
from server.utils.resource_utils import ResourceManager
from server.utils.response_util import value_error_collect



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
            "sig": str(body.sig),
            "owner": str(body.owner),
        })
        return NodeHandler(
            Feature,
            _body,
        ).create_node()



    """
        获取特性集
        url="/api/v1/feature", 
        methods=["Get"]
    """
    @auth.login_required()
    @response_collect
    @value_error_collect
    def get(self):
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
        features = StrategyHandler(Feature).get_query().all()
        _data = [feature.to_json() for feature in features]
        
        return jsonify(
            data = _data,
            error_code = RET.OK,
            error_msg = "OK"
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
        new_features = ReProductFeature.query.filter_by(product_id = product_id).all()
        new_feature_ids = list()
        [new_feature_ids.append(f.id) for f in new_features]
        if body.feature_id in new_feature_ids:
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "The feature is new, Please select an inherit feature."
            )

        p = Product.query.filter_by(id=product_id).first()
        products = Product.query.filter(
            Product.create_time >= p.create_time
        ).order_by(
            Product.create_time.asc(),
        ).all()

        if len(products) < 1:
            _data = []       

        _data = InheritFeatureHandler().create_relate_data(body, products)
            
        return jsonify(
            data = _data,
            error_code = RET.OK,
            error_msg = "OK"
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
        return NodeHandler(
            Feature,
            {"id": feature_id}
        ).get_node()



    """
        修改指定特性
        url="/api/v1/feature/<int:feature_id>", 
        methods=["Put"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
            feature = Feature.query.filter_by(id = feature_id).first()
            feature_put = Feature.query.filter_by(feature = body.feature).first()
            if feature_put and feature != feature_put:
                return jsonify(
                    error_code = RET.VERIFY_ERR,
                    error_msg = "The title of feature is exist, Please modify."
                )

        return NodeHandler(
            Feature,
            data
        ).put_node()



    """
        删除指定特性
        url="/api/v1/feature/<int:feature_id>", 
        methods=["Delete"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        return NodeHandler(
            Feature,
            {"id": feature_id}
        ).delete_node()



class ProductFeatureEvent(Resource):
    """
        查询指定产品下所有特性，包括新特性以及继承特性(Feature).
        url="/api/v1/product/<int:product_id>/feature", methods=["GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        _body = query.__dict__
        _body.update({
            "product_id": product_id,
        })
        
        return_data = list()
        _handler = ProductFeatureHandler(
            table=Feature, 
            re_table=ReProductFeature, 
        )
        
        _query = _handler.get_query(_has_re_table=True)
        filter_params = _handler.get_filter_params(
            product_id = product_id,
            query = query
        )

        product_features = _query.filter(*filter_params).all() 
        if not product_features:
            return jsonify(
                error_code = RET.OK,
                error_msg = "OK"
            )

        for p_f, feature in product_features:
            _feature_data = {
                **p_f.to_json(),
                **feature.to_json(),
            }
            return_data.append(_feature_data)
            
            strategy_commit = ProductFeatureHandler(
                table=Strategy, 
                re_table=StrategyCommit
            ).get_query(_has_re_table=True).filter(
                p_f.id == Strategy.product_feature_id,
                Strategy.id == StrategyCommit.strategy_id,
            ).first()
            
            if not strategy_commit:
                continue
            _feature_data.update(
                **strategy_commit[0].to_combine_json()
            )

        return jsonify(
            data = return_data,
            error_code = RET.OK,
            error_msg = "OK"
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
            id = product_feature_id
        ).first()
        if not product_feature:
            return jsonify(
                error_code = RET.NO_DATA_ERR, 
                error_msg = "The no. of re_product_feature {} is not exist".format(
                    product_feature_id
                )
            )
            
        strategy = Strategy.query.filter_by(
            product_feature_id = product_feature_id
        ).first()
        if not strategy:
            return jsonify(
                error_code = RET.OK, 
                error_msg = "The strategy is not exist."              
            )

        strategy_commit = StrategyHandler(
            Strategy,
            StrategyCommit
        ).get_query(_has_re_table=True).filter(
            product_feature_id == Strategy.product_feature_id,
            Strategy.id == StrategyCommit.strategy_id,
        ).first()
        
        if strategy_commit:
            return jsonify(
                data = strategy_commit[0].to_json(),
                error_code = RET.OK,
                error_msg = "OK"
            )
        else:
            return NodeHandler(
                Strategy,
                {"id": strategy.id}
            ).get_node()
            
        

    """
        创建测试策略
        url="/api/v1/product-feature/<int:product_feature_id>/strategy", 
        methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            product_feature_id = product_feature_id
        )
        return handler.create_strategy(product_feature_id, body)



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

        return NodeHandler(
            Strategy,
            {"id": strategy_id}
        ).get_node()



    """
        删除测试策略
        url="/api/v1/strategy/<int:strategy_id>", 
        methods=["Delete"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        StrategyEventHandler(
            StrategyCommit,
            Strategy,
            strategy_id = strategy_id
        ).check_commit_not_exist()

        return NodeHandler(
            Strategy,
            {"id": strategy_id}
        ).delete_node()



class StrategyTemplateEvent(Resource):
    """
        获取测试策略模板
        url="/api/v1/strategy-template", 
        methods=["Get"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        return NodeHandler(
            StrategyTemplate,
            query.__dict__
        ).get_query_nodes()



    """
        创建测试策略模板
        url="/api/v1/strategy-template", 
        methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        _body.update({
            "tree": json.dumps(body.tree)
        })
        return NodeHandler(
            StrategyTemplate,
            _body,
            filter_params=[
                StrategyTemplate.title == body.title
            ]
        ).create_node(
            is_addition_body = True
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
        return NodeHandler(
            StrategyTemplate,
            {"id": strategy_template_id}
        ).get_node()



    """
        修改测试策略模板
        url="/api/v1/strategy-template/<int:strategy_template_id>", 
        methods=["Put"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        if body.title:
            s_t = StrategyTemplate.query.filter_by(id = strategy_template_id).first()
            s_t_put = StrategyTemplate.query.filter_by(title = body.title).first()
            if s_t_put and s_t != s_t_put:
                return jsonify(
                    error_code = RET.VERIFY_ERR,
                    error_msg = "The title is exist, Please modify."
                )
        
        return NodeHandler(
            StrategyTemplate,
            _body,
        ).put_node()



    """
        删除测试策略模板
        url="/api/v1/strategy-template/<int:strategy_template_id>", 
        methods=["Delete"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
        return NodeHandler(
            StrategyTemplate,
            {"id" : strategy_template_id}
        ).delete_node()


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
        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            product_feature_id = product_feature_id
        )
        handler.check_strategy_exist(False) 
        handler.check_commit_not_exist()   
        handler.check_feature_exist() 

        s_t = StrategyTemplate.query.filter_by(
            id = strategy_template_id
        ).first()
        if not s_t:
            return jsonify(
                error_code = RET.NO_DATA_ERR,
                error_msg = "The strategy template is not exist."
            )
        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            product_feature_id = product_feature_id
        )
        return handler.create_strategy(
            product_feature_id, 
            StrategyBodySchema(**
                {
                    "tree": json.loads(s_t.tree),
                }
            )
        )



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
    def post(self, strategy_id, body: CommitBodySchema):
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
        check_handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            strategy_id = strategy_id
        )
        strategy = check_handler.check_strategy_exist()  
        check_handler.check_commit_creator()
        check_handler.check_commit_status()
        
        strategy_commit = StrategyCommit.query.filter_by(
            strategy_id = strategy.id
        ).first()
        
        if not strategy_commit:
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "The strategy_commit is not exist."
            )

        NodeHandler(  
            StrategyCommit,
            {
                "commit_status": "submitted", 
                "id": strategy_commit.id
            }
        ).put_node()

        try:             
            handler = CommitHandler(strategy_id)
            handler.create_fork()
            
            handler.create_branch()
            # 需要将tree转成md_content
            md_content = strategy_commit.commit_tree
            
            handler.git_operate(md_content)
            
            handler.create_pull_request(body=body.__dict__)  
        except (RuntimeError, ValueError, TypeError) as e:
            NodeHandler(  
                StrategyCommit,
                {
                    "commit_status": "staged",
                    "id": strategy_commit.id
                }
            ).put_node()
            
            return jsonify(
                error_code = RET.RUNTIME_ERROR,
                error_msg = str(e)
            )
        return jsonify(
            error_code = RET.OK,
            error_msg = "OK"
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
        
        
        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            strategy_id = strategy_id
        )
        handler.check_strategy_exist() 
        is_exist = handler.check_commit() 
        if is_exist: 
            handler.check_commit_creator()
            handler.check_commit_status() 

            strategy_commit = StrategyCommit.query.filter_by(
                strategy_id = strategy_id
            ).first()

            _body.update({
                "id": strategy_commit.id
            })

            return NodeHandler(
                StrategyCommit,
                _body
            ).put_node()
        else:
            return NodeHandler(
                StrategyCommit,
                _body
            ).create_node()



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
                error_code = RET.OK,
                error_msg = "The strategy is not exist."
            )
        
        s_c = StrategyCommit.query.filter_by(strategy_id = strategy.id).first()
        if not s_c:
            return jsonify(
                error_code = RET.OK,
                error_msg = "The strategy-commit is not exist."
            )
        
        return NodeHandler(
            StrategyCommit,
            {"id": s_c.id}
        ).get_node()



    @auth.login_required()
    @response_collect
    @validate()
    @value_error_collect
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
            "id" : strategy_commit_id,
            "commit_tree": json.dumps(body.commit_tree)
        })

        return NodeHandler(
            StrategyCommit,
            _body
        ).put_node()



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
        strategy_commit = StrategyCommit.query.filter_by(
            strategy_id = strategy_id
        ).first()
        
        if not strategy_commit:
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "The strategy_commit is not exist."
            )
        
        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            strategy_commit_id = strategy_commit.id
        )
        handler.check_commit_creator()
        handler.check_commit_status()
        return NodeHandler(
            StrategyCommit,
            {"id": strategy_commit.id}
        ).delete_node()



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
                error_code = RET.OK,
                error_msg = "The older product is not exist."  
            )

        fs,_data = list(), list()
        fs = InheritFeatureHandler().get_all_feature(product)
        if fs:
            _data = InheritFeatureHandler(product_id).create_inherit_data(fs) 
        return jsonify(
            data = _data,
            error_code = RET.OK,
            error_msg = "OK"
        )
