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
# 基线模板(Baseline_template)相关接口的handler层

import json

from flask import jsonify, g, current_app
import sqlalchemy

from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.db import Insert, collect_sql_error
from server.utils.permission_utils import GetAllByPermission
from server.model.testcase import CaseNode, Baseline
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager



class BaselineTemplateHandler:
    @staticmethod
    @collect_sql_error
    def get(baseline_template_id):
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The baseline_template does not exist."
            )

        root_filter_params = [
            BaseNode.is_root.is_(True),
            BaseNode.baseline_template_id == baseline_template_id,
        ]
        
        root_node = BaseNode.query.filter(*root_filter_params).first()
        if not root_node:
            return {"data": {"text": "新建"}}
        
        res_items = BaselineTemplateHandler.get_all_children(root_node) 
        return res_items


    @staticmethod
    @collect_sql_error
    def get_all_children(base_node):

        if not base_node.children:
            return base_node.to_json()
        
        return_data = {
            **base_node.to_json(),
            "children": []
        }

        for child in base_node.children:
            return_data["children"].append(BaselineTemplateHandler.get_all_children(child))
        return return_data


    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = GetAllByPermission(BaselineTemplate).get_filter()
        
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'title':
                filter_params.append(BaselineTemplate.title.like(f'%{value}%'))
            if key == 'group_id':
                filter_params.append(BaselineTemplate.group_id == value)
                filter_params.append(BaselineTemplate.permission_type == 'group')
            if key == 'org_id':
                filter_params.append(BaselineTemplate.org_id == value)
                filter_params.append(BaselineTemplate.permission_type == 'org')
            if key == 'openable':
                filter_params.append(BaselineTemplate.openable == value)                 
        baselinetemps = BaselineTemplate.query.filter(*filter_params).all()
        
        return_data = [baseline_template.to_json() for baseline_template in baselinetemps]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


    @staticmethod
    @collect_sql_error
    def check_impl(baseline_template, inherit_baseline_template):
        if baseline_template.type == inherit_baseline_template.type:
            if baseline_template.type == "org" and \
                baseline_template.org_id != inherit_baseline_template.org_id:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The org_id of two baseline_template is not equal."
                )
            if baseline_template.type == "group" and \
                baseline_template.group_id != inherit_baseline_template.group_id:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The group_id of two baseline_template is not equal."
                )
        elif baseline_template.org_id != inherit_baseline_template.org_id:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The org_id of two baseline_template is not equal or not right."
            )
        return jsonify(error_code=RET.OK, error_msg="OK")


    @staticmethod
    @collect_sql_error
    def impl_select_base_node_casenode(baseline_template, base_node):
        _casenode = None
        
        filter_params = [
            CaseNode.permission_type== baseline_template.type,
            CaseNode.baseline_id == sqlalchemy.null()
        ]

        if base_node.case_node_id:
            casenode = CaseNode.query.filter_by(id=base_node.case_node_id).first()
            
            if baseline_template.type == base_node.type:
                _casenode = casenode
            else:
                if casenode.suite_id:
                    filter_params.append(CaseNode.suite_id == casenode.suite_id)
                elif casenode.case_id:
                    filter_params.append(CaseNode.case_id == casenode.case_id)   
                else:
                    filter_params.append(CaseNode.title == base_node.title) 
                
                _casenode = CaseNode.query.filter(*filter_params).first()
        return _casenode


    @staticmethod
    @collect_sql_error
    def create_new_base_node(baseline_template, base_node, casenode, res_node, nodes):
        node_body = base_node.to_json()
        if base_node.is_root:
                node_body.update({
                    "is_root": True
                })                         
        node_body.pop("id")
        node_body.update({
            "baseline_template_id": baseline_template.id,
            "permission_type": base_node.permission_type,
            "type": base_node.type,
            "creator_id": g.gitee_id,
            "case_node_id": casenode.id if casenode is not None else None,
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        })
        if node_body["type"] == "group":
            node_body.update({
                "group_id": base_node.group_id
        })

        resp = ResourceManager("base_node").add_v2(
            "baseline_template/api_infos.yaml",
            node_body
        )
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp
        _id = _resp.get("data").get("id")
        
        for key, value in res_node.items():
            if base_node in value:
                parent = BaseNode.query.filter_by(id=key).first()
                child = BaseNode.query.filter_by(id=_id).first()
                child.parent.append(parent)
                child.add_update() 
                        
        nodes.append(_id)
        return _id, nodes


    @staticmethod
    @collect_sql_error
    def check_base_node_not_exist(base_node, res_old_base_nodes):
        flag = False            
        if not res_old_base_nodes:
            flag = True
            return flag
        if base_node.title not in list(
            map(lambda node: node.get("title"), res_old_base_nodes)
        ):
            if base_node.case_node_id is not None:
                for old_base_node in res_old_base_nodes:
                    if ((
                        old_base_node["case_node_id"] != base_node.case_node_id,
                    )):
                        
                        flag = True
            else:
                flag = True
        if base_node.is_root:
            flag = False
        return flag


    @staticmethod
    @collect_sql_error
    def inherit(baseline_template_id, inherit_baseline_template_id):
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="baseline_template does not exist"
            )

        inherit_baseline_template = BaselineTemplate.query.filter(
            BaselineTemplate.id == inherit_baseline_template_id,
            BaselineTemplate.openable == 1,
            ).first()
        if not inherit_baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="inherit_baseline_template does not exist or not openable."
            )

        resp = BaselineTemplateHandler.check_impl(baseline_template, inherit_baseline_template)
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp
        
        old_root_base_node = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
            BaseNode.is_root == 1,
            ).first()
        if not old_root_base_node:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="The root node of baseLineTemplate is empty.")

        res_old_nodes = list()
        res_old_base_nodes = list()
        old_base_nodes = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
        ).all()

        for base_node in old_base_nodes:
            res_old_nodes.append(base_node)
            res_old_base_nodes.append(base_node.to_json())

        base_nodes = BaseNode.query.filter(
            BaseNode.baseline_template_id == inherit_baseline_template_id,
        ).all()

        if not base_nodes:
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "base_nodes does not exist."
            )
        
        nodes = list()
        res_node = dict()
        for base_node in base_nodes:
            if not base_node:
                return jsonify(
                    error_code = RET.VERIFY_ERR,
                    error_msg = "base_node does not exist."
                )

            _casenode = BaselineTemplateHandler.impl_select_base_node_casenode(
                baseline_template, 
                base_node
            )

            flag = BaselineTemplateHandler.check_base_node_not_exist(
                base_node, 
                res_old_base_nodes
            )
            
            if flag:
                resp = BaselineTemplateHandler.create_new_base_node(
                    baseline_template, base_node, _casenode, res_node, nodes
                )
                if type(resp) == tuple:
                    _id, nodes = resp 
                else:
                    return resp  
            else:
                for node in res_old_base_nodes:
                    if node.get("title") == base_node.title:
                        _id = node.get("id")
                        break
                    elif base_node.is_root == 1:
                        _id = old_root_base_node.id
                        break
                    else:
                        _id = None
            
            children = base_node.children
            
            children_list = []
            [children_list.append(child) for child in children]
            if children and _id:
                res_node.update({
                    _id: children_list
                })

        return jsonify(error_code=RET.OK, error_msg="OK", data=nodes)



class BaseNodeHandler:
    @staticmethod
    @collect_sql_error
    def get(base_node_id):
        base_node = BaseNode.query.filter_by(id=base_node_id).first()
        if not base_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="This base node does not exist"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=base_node.to_json()
        )


    @staticmethod
    @collect_sql_error
    def get_all(baseline_template_id, query):
        filter_params = GetAllByPermission(BaseNode).get_filter()
        filter_params.append(
            BaseNode.baseline_template_id == baseline_template_id
        )
        
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'case_node_id':
                filter_params.append(BaseNode.case_node_id == value)
            if key == 'group_id':
                filter_params.append(BaseNode.group_id == value)
            if key == 'org_id':
                filter_params.append(BaseNode.org_id == value)

        base_nodes = BaseNode.query.filter(*filter_params).all()
        return_data = [base_node.to_json() for base_node in base_nodes]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


    @staticmethod
    @collect_sql_error
    def post(baseline_template_id, body):
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="baseline_template does not exists"
            )

        _body = body.__dict__
        _body.update({
            "creator_id": g.gitee_id,
            "group_id": baseline_template.group_id,
            "org_id": baseline_template.org_id,
            "baseline_template_id": baseline_template.id,
            "permission_type": baseline_template.permission_type,
        })

        if body.case_node_id:
            case_node = CaseNode.query.filter(
                CaseNode.id == body.case_node_id,
            ).first()
            if not case_node:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, 
                    error_msg="the case node to relate does not exists"
                )
            _body.update({
                "title": case_node.title,
                "type": case_node.type,
            })
 
        resp = ResourceManager("base_node").add_v2(
            "baseline_template/api_infos.yaml",
            _body
        )
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp
        
        base_node_id = _resp.get("data").get("id")

        if body.parent_id:
            child = BaseNode.query.filter_by(id=base_node_id).first()
            parent = BaseNode.query.filter_by(id=body.parent_id).first()
            if not parent:
                return jsonify(
                    error_code=RET.NO_DATA_ERR, 
                    error_msg="parent node does not exists"
                )

            child.parent.append(parent)
            child.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK", data=base_node_id)


    @staticmethod
    @collect_sql_error
    def delete(base_node_id):
        base_node = BaseNode.query.filter_by(id=base_node_id).first()
        if not base_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The base_node does not exist."
            )

        return ResourceManager("base_node").del_single(base_node_id)


class BaselineTemplateApplyHandler:
    @staticmethod
    @collect_sql_error
    def check_base_node_not_exist(base_node, casenode, res_old_casenode):
        flag = False

        if not res_old_casenode:
            flag = True
            return flag
        
        if base_node.title not in list(
            map(lambda node: node.get("title"), res_old_casenode)
        ):
            if casenode and (casenode.type in ["suite", "case"]):
                for old_casenode in res_old_casenode:
                    if (
                        old_casenode["suite_id"] != casenode.suite_id
                    ) or (
                        old_casenode["case_id"] != casenode.case_id
                    ):
                        flag = True
            else:
                flag = True
       
        return flag


    @staticmethod
    @collect_sql_error
    def create_new_casenode(base_node, baseline, casenode, res_node, nodes):
        root_casenode = CaseNode.query.filter_by(
            baseline_id = baseline.id,
            type = "baseline",
        ).first()

        if not casenode:
            node_body = base_node.to_json()
        else:
            node_body = casenode.to_json()

        node_body.pop("id")
        node_body.update({
            "is_root": False,
            "baseline_id": baseline.id,
            "type": base_node.type,
            "permission_type":baseline.permission_type,
            "milestone_id": baseline.milestone_id,
            "creator_id": g.gitee_id,
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        })
        if baseline.permission_type == "group":
            node_body.update({
                "group_id": baseline.group_id
        })

        _id = Insert(CaseNode, node_body).insert_id(CaseNode, "/case_node")
        child = CaseNode.query.filter_by(id=_id).first()

        for key, value in res_node.items():
            if base_node in value:
                parent = CaseNode.query.filter_by(id=key).first()
                child.parent.append(parent)
                child.add_update()
               
        if len(child.parent.all()) == 0:
            child.parent.append(root_casenode)
            child.add_update()

        nodes.append(_id)
        return _id, nodes


    @staticmethod
    @collect_sql_error
    def check_org_group(baseline_id, baseline_template_id):
        baseline = CaseNode.query.filter_by(baseline_id=baseline_id).first()
        if not baseline:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The baseline is not exist."
            )            

        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The baseline_template is not exist."
            )

        if baseline.permission_type == baseline_template.type == "org":
            if baseline.org_id != baseline_template.org_id:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="Orgs cannot be applied to each other."
                ) 

        if baseline.permission_type == baseline_template.type == "group":
            if baseline.group_id != baseline_template.group_id:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="Groups cannot be applied to each other."        
                )

        if baseline.permission_type != baseline_template.type:
            if baseline.org_id != baseline_template.org_id:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="Orgs cannot be applied to each other."
                ) 

        return jsonify(error_code=RET.OK, error_msg="OK")        


    @staticmethod
    @collect_sql_error
    def check_node_not_equal(case_node_old, base_node, res_new_basenode):
        check_flag = False
        
        old_parent = CaseNode.query.filter(CaseNode.children.contains(case_node_old)).first()
        base_parent = BaseNode.query.filter(BaseNode.children.contains(base_node)).first()
        if old_parent.title not in list(map(lambda node: node.get("title"), res_new_basenode)) \
            and old_parent.title != base_parent.title: 
            check_flag = True

        return check_flag


    @staticmethod
    @collect_sql_error
    def apply_select_casenode(baseline, base_node):
        _casenode = None
        _casenode_old = None
        
        filter_params = [
            CaseNode.permission_type == baseline.permission_type,
            CaseNode.baseline_id == sqlalchemy.null(),
        ]

        filter_params_old = [
            CaseNode.permission_type == baseline.permission_type,
            CaseNode.baseline_id == baseline.id,
        ]

        if base_node.case_node_id:
            casenode = CaseNode.query.filter_by(id=base_node.case_node_id).first()
            if not casenode:
                return jsonify(
                    error_code=RET.VERIFY_ERR,
                    error_msg="The case-node associated with the base-node does not exist."
                )
            
            if baseline.permission_type == base_node.type:
                _casenode = casenode
            else:
                if casenode.suite_id:
                    filter_params.append(CaseNode.suite_id == casenode.suite_id)
                    filter_params_old.append(CaseNode.suite_id == casenode.suite_id)
                elif casenode.case_id:
                    filter_params.append(CaseNode.case_id == casenode.case_id) 
                    filter_params_old.append(CaseNode.case_id == casenode.case_id)  
                else:
                    filter_params.append(CaseNode.title == base_node.title) 
                    filter_params_old.append(CaseNode.title == base_node.title) 
                _casenode = CaseNode.query.filter(*filter_params).first()
        else:
            filter_params_old.append(CaseNode.title == base_node.title)
        _casenode_old = CaseNode.query.filter(*filter_params_old).first()
        
        return _casenode, _casenode_old

    @staticmethod
    @collect_sql_error
    def modify_bind(case_node_old, base_node, map_node):
        case_parent_id = None
        old_parent = CaseNode.query.filter(CaseNode.children.contains(case_node_old)).first()
        base_parent = BaseNode.query.filter(BaseNode.children.contains(base_node)).first()

        if map_node:
            for key, value in map_node.items():
                if base_parent.id == value:
                    case_parent_id = key
                    break
            if case_parent_id:
                case_parent = CaseNode.query.filter_by(id=case_parent_id).first()
            
                case_node_old.parent.remove(old_parent)
                case_node_old.parent.append(case_parent)
                case_node_old.add_update()  


    @staticmethod
    @collect_sql_error
    def apply(case_node_id, baseline_template_id):
        baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id,
            openable=1
        ).first()
        if not baseline_template:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The baseline_template is not openable, cannot apply."
            )
        
        casenode = CaseNode.query.filter_by(id=case_node_id).first()
        baseline = Baseline.query.filter(
            Baseline.case_nodes.contains(casenode)
        ).first()
        if not baseline:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The baseline is not exist."
            )
        
        baseline_id = baseline.id
        resp = BaselineTemplateApplyHandler.check_org_group(
            baseline_id, baseline_template_id
        )
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp 

        res_old_casenode = list()
        res_new_basenode = list()
        old_casenodes = CaseNode.query.filter(
            CaseNode.baseline_id == baseline_id,
            CaseNode.type != "baseline"
            ).all()
        [res_old_casenode.append(casenode.to_json()) for casenode in old_casenodes]

        base_nodes = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
            BaseNode.is_root.isnot(True),
            ).all()
        [res_new_basenode.append(basenode.to_json()) for basenode in base_nodes]

        nodes = list()
        res_node = dict()
        map_node = dict()
        for base_node in base_nodes:
            _casenode, _case_node_old = BaselineTemplateApplyHandler.apply_select_casenode(
                baseline, base_node
            )
            flag = BaselineTemplateApplyHandler.check_base_node_not_exist(
                base_node, _casenode, res_old_casenode
            )

            if flag:
                resp = BaselineTemplateApplyHandler.create_new_casenode(
                    base_node, baseline, _casenode, res_node, nodes
                )

                if type(resp) == tuple:
                    _id, nodes = resp 
                else:
                    return resp
            else:
                if not _case_node_old:
                    return jsonify(
                        error_code=RET.VERIFY_ERR,
                        error_msg="The case_node_old is not exist." 
                    )
                _id = _case_node_old.id

                check_flag = BaselineTemplateApplyHandler.check_node_not_equal(
                   _case_node_old, base_node, res_new_basenode
                )
                if check_flag:
                    BaselineTemplateApplyHandler.modify_bind(
                        _case_node_old, base_node, map_node
                    )

            children = base_node.children
            children_list = []
            [children_list.append(child) for child in children]
            if children:
                res_node.update({
                    _id: children_list
                })
            
            map_node.update({
                _id: base_node.id
            })

        return jsonify(error_code=RET.OK, error_msg="OK", data=nodes)