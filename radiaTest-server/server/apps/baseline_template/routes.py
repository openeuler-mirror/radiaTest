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
# 基线模板(Baseline_template)相关接口的route层
from flask import g, jsonify
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from server import redis_client, db, swagger_adapt
from server.schema.base import QueryBaseModel
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect, workspace_error_collect
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.utils.db import collect_sql_error
from server.schema.baselinetemplate import (
    BaselineTemplateBodySchema,
    BaselineTemplateQuerySchema,
    BaselineTemplateUpdateSchema,
    BaseNodeBodySchema,
    BaseNodeUpdateSchema,
    BaseNodeQuerySchema,
)
from server.apps.baseline_template.handler import (
    BaseNodeHandler,
    BaselineTemplateApplyHandler,
    BaselineTemplateHandler,
)
from server.utils.permission_utils import GetAllByPermission


def get_baseline_template_tag():
    return {
        "name": "基线模板",
        "description": "基线模板接口",
    }


class BaselineTemplateEvent(Resource):
    """
        创建、查询基线模板(Baseline_template).
        url="/api/v1/baseline-template", methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "新增基线模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": BaselineTemplateBodySchema,
    })
    def post(self, body: BaselineTemplateBodySchema):        
        """
            在数据库中新增Baseline_template数据, 并新增该模板首节点Base_Node.
            请求体:
            {
                "title": str,
                "openable": bool,
                "type": str,
                "group_id": int
            }
            返回体:
            {
                "data": {
                    "id": int
                },
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        baseline_template = BaselineTemplate.query.filter_by(title=body.title).all()
        if baseline_template:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="The title of baseline_template {} has already exist".format(
                    body.title
                ),
            )

        if body.org_id:
            org_id = body.org_id
        else:
            org_id = redis_client.hget(
                RedisKey.user(g.user_id), 
                'current_org_id'
            )
            
        baseline_template = BaselineTemplate(
            title=body.title,
            type=body.type,
            permission_type=body.type,
            openable=body.openable,
            creator_id=g.user_id,
            org_id=org_id,
            group_id=body.group_id,
        )
        db.session.add(baseline_template)
        db.session.commit()

        new_baseline_template = BaselineTemplate.query.filter_by(title=body.title).first()

        _base_node = BaseNode(
            title=body.title,
            creator_id=g.user_id,
            group_id=new_baseline_template.group_id,
            org_id=new_baseline_template.org_id,
            permission_type=new_baseline_template.permission_type,
            baseline_template_id=new_baseline_template.id,
            type="baseline",
            is_root=True,
        )
        db.session.add(_base_node)
        db.session.commit()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )

    @auth.login_check
    @response_collect
    @workspace_error_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "搜索基线模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": BaselineTemplateQuerySchema,   # 当前接口查询参数schema校验器
    })
    def get(self, workspace: str, query: BaselineTemplateQuerySchema):
        """
            API: /api/v1/baseline-template?group_id=1
            返回体:
            {
            "data": [
                {
                "group_id": int,
                "id": int,
                "openable": bool,
                "org_id": int,
                "title": str,
                "type": str
                },
            ],
            "error_code": "2000",
            "error_msg": "OK"
            }
        """
        return BaselineTemplateHandler.get_all(query, workspace)


class BaselineTemplateInheritEvent(Resource):
    """
        继承指定基线模板
        url="/api/v1/baseline-template/<int:baseline_template_id>/inherit/<int:inherit_baseline_template_id>", 
        methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateInheritEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "基线模板继承",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, baseline_template_id, inherit_baseline_template_id):
        """
            在数据库中新增Baseline_template数据, 并新增该模板首节点Base_Node.
            API: "/api/v1/baseline-template/<int:baseline_template_id>/inherit/<int:inherit_baseline_template_id>"
            返回体:
            {
            "data": [
                int,
                int
            ],
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """      
        return BaselineTemplateHandler.inherit(
            baseline_template_id, 
            inherit_baseline_template_id
        )


class BaselineTemplateItemEvent(Resource):
    """
        查询、修改、删除指定基线模板
        url="/api/v1/baseline-template/<int:baseline_template_id>", 
        methods=["GET", "PUT", "DELETE"]
    """
    @auth.login_required()
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "修改基线模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": BaselineTemplateUpdateSchema,  # 当前接口请求体参数schema校验器
    })
    def put(self, baseline_template_id, body: BaselineTemplateUpdateSchema):
        """
            在数据库中修改Baseline_template数据, 并修改该模板首节点Base_Node.
            请求体:
            {
            "title": str,
            "openable": bool
            }
            返回体:
            {
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline_template is not exist."
            )
        if body.title:
            baseline_template_title = BaselineTemplate.query.filter_by(
                title=body.title
            ).first()
            if baseline_template_title and baseline_template_title.id != baseline_template_id:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg=f"The baseline template {body.title} has existed."
                )
            baseline_template.title = body.title
        if body.openable is not None:
            baseline_template.openable = body.openable
        baseline_template.add_update(BaselineTemplate, "/baseline_template")
            
  
        _base_node = BaseNode.query.filter_by(
            baseline_template_id=baseline_template_id,
            is_root=True,
        ).first()
        if _base_node and body.title:
            _base_node.title = body.title
            _base_node.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "删除基线模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, baseline_template_id):
        """
            在数据库中删除Baseline_template数据.
            API:/api/v1/baseline-template/<int:baseline_template_id>
            请求体:
            {}
            返回体:
            {
            "error_code": "2000",
            "error_msg": "Request processed successfully."
            }
        """

        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline_template does not exist."
            )
        db.session.delete(baseline_template)
        db.session.commit()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK."
        )

    @auth.login_check
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "获取基线模板信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": QueryBaseModel
    })
    def get(self, baseline_template_id, query: QueryBaseModel):
        """
            在数据库中查询Baseline_template数据.
            API:/api/v1/baseline-template/<int:baseline_template_id>
            返回体:
            {
            "data": {
                "baseline_template_id": int,
                "case_node_id":int,
                "children": [],
                "data": {
                "id": int,
                "text": str
                },
                "group_id": int,
                "id": int,
                "is_root": bool,
                "org_id": int,
                "title": str,
                "type": str
            },
            "error_code": "2000",
            "error_msg": "OK"
            }
        """
        filter_params = GetAllByPermission(BaselineTemplate, org_id=query.org_id).get_filter()
        filter_params.append(BaselineTemplate.id == baseline_template_id)
        baseline_template = BaselineTemplate.query.filter(
            *filter_params
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline template does not exist."
            )
        if not hasattr(g, "user_id"):
            if baseline_template.openable is False:
                return jsonify(
                    error_code=RET.DB_DATA_ERR,
                    error_msg="have no right.",
                )
        else:
            if baseline_template.creator_id != g.user_id and baseline_template.openable is False:
                return jsonify(
                    error_code=RET.DB_DATA_ERR,
                    error_msg="have no right.",
                )

        return_data = BaselineTemplateHandler().get(baseline_template_id)
        return jsonify(
            error_code=RET.OK,
            error_msg="OK.",
            data=return_data
        )


class BaseNodeEvent(Resource):
    """
        创建、查询基线模板节点(BaseNode).
        url="/api/v1/baseline-template/<int:baseline_template_id>/base-node", 
        methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaseNodeEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "基线模板下新增节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": BaseNodeBodySchema,  # 当前接口请求体参数schema校验器
    })
    def post(self, baseline_template_id, body: BaseNodeBodySchema):
        """
            在数据库中新增BaseNode数据.
            请求体:
            {
                "is_root": bool,
                "parent_id": int,
                "title": str,
                "type": str,
                "case_node_ids": List[int],
            }
            返回体:
            {
                "data": int,
                "error_code": "2000",
                "error_msg": "OK"
            }
        """
        return BaseNodeHandler.post(baseline_template_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaseNodeEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "查询基线模板下所有节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "query_schema_model": BaseNodeQuerySchema,
    })
    def get(self, baseline_template_id, query: BaseNodeQuerySchema):
        """
            在数据库中查询BaseNode数据.
            API:/api/v1/base-node/<int:base_node_id>?case_node_id=case_node_id
            返回体:
            {
            "data": int,
            "error_code": "2000",
            "error_msg": "OK"
            }
        """
        return BaseNodeHandler.get_all(baseline_template_id, query)


class BaseNodeItemEvent(Resource):
    """
        查询、修改、删除指定基线节点
        url="/api/v1/base-node/<int:base_node_id>", 
        methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "获取节点信息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def get(self, base_node_id: int):
        """
            在数据库中查询指定BaseNode数据.
            请求体:
            {
            "is_root": bool,
            "parent_id": int,
            "title": str
            }
            返回体:
            {
            "baseline_template_id": int,
            "case_node_id": int,
            "data": {
                "id": int,
                "text": str
            },
            "group_id": int,
            "id": int,
            "is_root": bool,
            "org_id": int,
            "title": str,
            "type": str
            }
        """
        return BaseNodeHandler.get(base_node_id)

    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "删除指定节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, base_node_id):
        """
            在数据库中删除指定BaseNode数据.
            请求体:
            {}
            返回体:
            {
            "error_code": "2000",
            "error_msg": "Request processed successfully."
            }
        """
        return BaseNodeHandler.delete(base_node_id)

    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaseNodeItemEvent",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "修改指定节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        "request_schema_model": BaseNodeUpdateSchema,
    })
    def put(self, base_node_id, body: BaseNodeUpdateSchema):
        """
            在数据库中修改指定BaseNode数据.
            请求体:
            {
            "title": "test-hello-mode"
            }
            返回体:
            {
            "error_code": "2000",
            "error_msg": "Request processed successfully."
            }
        """
        base_node = BaseNode.query.filter_by(id=base_node_id).first()
        if base_node.case_node_id:
            return jsonify(
                error_code=RET.VERIFY_ERR, 
                error_msg="Associated node cannot be modified."
            )
        if base_node.parent:
            parent = base_node.parent[0]
            for node in parent.children:
                if node.title == body.title:
                    return jsonify(
                        error_code=RET.DATA_EXIST_ERR, 
                        error_msg=f"{body.title} has existed."
                    )
        base_node.title = body.title
        base_node.add_update(BaseNode, "/base_node")
        return jsonify(
            error_code=RET.OK, 
            error_msg="OK."
        )


class BaselineTemplateCleanItemEvent(Resource):
    """
        清空指定基线模板
        url="/api/v1/baseline-template/<int:baseline_template_id>/clean", 
        methods=["DELETE"]
    """
    @auth.login_required()
    @response_collect
    @collect_sql_error
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateCleanItemEvent",  # 当前接口视图函数名
        "func_name": "delete",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "清空指定模板下的所有节点",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def delete(self, baseline_template_id):
        """
            在数据库中清空指定BaselineTemplate数据.
            请求体:
            {}
            返回体:
            {
            "error_code": "2000",
            "error_msg": "Request processed successfully."
            }
        """
        root_base_node = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
            BaseNode.is_root.is_(True)
        ).first()
        if not root_base_node:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Base node doesn't existed.")
        
        for base_node in root_base_node.children:
            db.session.delete(base_node)
        db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK.")


class BaselineTemplateApplyItemEvent(Resource):
    """
        给指定基线(case_node节点)应用指定模板.
        url="/api/v1/case-node/<int:case_node_id>/apply/baseline-template/<int:baseline_template_id>", 
        methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_baseline_template_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "BaselineTemplateApplyItemEvent",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_baseline_template_tag(),  # 当前接口所对应的标签
        "summary": "给指定基线应用指定模板",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
    })
    def post(self, case_node_id, baseline_template_id):
        """
            在数据库中新增Baseline_template的同样数据至Baseline表.
            API: "/api/v1/case-node/<int:case_node_id>/apply/baseline-template/<int:baseline_template_id>"
            返回体:
            {
            "data": [
                int,
                int
            ],
            "error_code": "2000",
            "error_msg": "OK"
            }  
        """  
        try:
            handler = BaselineTemplateApplyHandler(case_node_id, baseline_template_id)
            handler.check_valid()
            handler.apply()
        
        except ValueError as e:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg=str(e),
            )
        
        except (SQLAlchemyError, IntegrityError) as e:
            return jsonify(
                error_code=RET.DB_ERR,
                error_msg=str(e)
            )
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=handler.applied_list,
        )
