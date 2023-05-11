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

import json
from flask import request, g, jsonify, current_app, Response
from flask_restful import Resource
from flask_pydantic import validate
from sqlalchemy import or_, and_
from server import redis_client, casbin_enforcer
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect, workspace_error_collect
from server.utils.permission_utils import GetAllByPermission
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.utils.db import Insert, Edit, Delete, collect_sql_error
from server.schema.base import PageBaseSchema
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
    BaselineTemplateHandler,
    BaselineTemplateApplyHandler,
)
from server.utils.resource_utils import ResourceManager


class BaselineTemplateEvent(Resource):
    """
        创建、查询基线模板(Baseline_template).
        url="/api/v1/baseline-template", methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
            
        _body = {
            "title": body.title,
            "type": body.type,
            "permission_type": body.type,
            "openable": body.openable,
            "creator_id": g.user_id,
            "org_id": org_id,
            "group_id": body.group_id,
        }

        _resp = ResourceManager("baseline_template").add("api_infos.yaml", _body)
        resp_dict = json.loads(_resp.response[0])
        new_baseline_template_id = resp_dict.get("data").get("id")
        new_baseline_template = BaselineTemplate.query.filter_by(id=new_baseline_template_id).first()

        _base_node_body = {
            "title": body.title,
            "creator_id": g.user_id,
            "openable": new_baseline_template.openable,
            "group_id": new_baseline_template.group_id,
            "org_id": new_baseline_template.org_id,
            "permission_type": new_baseline_template.permission_type,
            "baseline_template_id": new_baseline_template_id,
            "type": "baseline",
            "is_root": True,
        }

        return ResourceManager("base_node").add_v2(
            "baseline_template/api_infos.yaml",
            _base_node_body,
        )


    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
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
    @casbin_enforcer.enforcer
    @collect_sql_error
    @validate()
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
                "data": {
                    "id": int
                },
                "error_code": "2000",
                "error_msg": "Request processed successfully."
            }
        """
        _body = body.__dict__
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline_template is not exist."
            )

        _body.update({"id": baseline_template_id})
        Edit(BaselineTemplate, _body).single(BaselineTemplate, "/baseline_template")

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
    @casbin_enforcer.enforcer
    @validate()
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
        return ResourceManager("baseline_template").del_single(baseline_template_id)


    @auth.login_required()
    @response_collect
    @validate()
    def get(self, baseline_template_id):
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
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline_template is not exist."
            )
        if baseline_template.openable:
            return BaselineTemplatePrivateItemEvent.get(baseline_template_id)
        else:
            return BaselineTemplatePrivateItemEvent.get_priavicy(baseline_template_id)



class BaselineTemplatePrivateItemEvent():
    """
        选择使用casbin方法:是否使用casbin查询指定基线模板
    """
    @auth.login_required()
    @response_collect
    @validate()
    def get(baseline_template_id):
        """
            选择使用casbin方法:不带casbin查询指定基线模板
        """
        return_data = BaselineTemplateHandler().get(baseline_template_id)
        
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
    def get_priavicy(baseline_template_id):
        """
            私有方法:带casbin查询指定基线模板
        """
        return_data = BaselineTemplateHandler().get(baseline_template_id)
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)



class BaseNodeEvent(Resource):
    """
        创建、查询基线模板节点(BaseNode).
        url="/api/v1/baseline-template/<int:baseline_template_id>/base-node", 
        methods=["POST", "GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, baseline_template_id, body: BaseNodeBodySchema):
        """
            在数据库中新增BaseNode数据.
            请求体:
            {
            "is_root": bool,
            "parent_id": int,
            "title": str
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
    @casbin_enforcer.enforcer
    @response_collect
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
    @casbin_enforcer.enforcer
    @validate()
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
        _body = body.__dict__
        _body.update({
            "id": base_node_id
        })
        base_node = BaseNode.query.filter_by(id=base_node_id).first()
        if base_node.case_node_id:
            return jsonify(
                error_code=RET.VERIFY_ERR, 
                error_msg="Associated node cannot be modified."
            )
        return Edit(BaseNode, _body).single(BaseNode, "/base_node")


class BaselineTemplateCleanItemEvent(Resource):
    """
        清空指定基线模板
        url="/api/v1/baseline-template/<int:baseline_template_id>/clean", 
        methods=["DELETE"]
    """
    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    @validate()
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
        base_node_list = list()
        
        base_nodes = BaseNode.query.filter_by(
            baseline_template_id=baseline_template_id,
            is_root=0
        ).all()
        if not base_nodes:
            return jsonify(error_code=RET.OK, error_msg="OK")
        
        [base_node_list.append(base_node.id) for base_node in base_nodes]
        return ResourceManager("base_node").del_batch(base_node_list)
        


class BaselineTemplateApplyItemEvent(Resource):
    """
        给指定基线(case_node节点)应用指定模板.
        url="/api/v1/case-node/<int:case_node_id>/apply/baseline-template/<int:baseline_template_id>", 
        methods=["POST"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        return BaselineTemplateApplyHandler.apply(
            case_node_id, 
            baseline_template_id
        )
