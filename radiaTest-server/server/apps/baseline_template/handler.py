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
from flask import jsonify, g
import sqlalchemy
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.db import collect_sql_error
from server.model.testcase import CaseNode
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.utils.permission_utils import GetAllByPermission


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
    def get_all(query, workspace=None):
        filter_params = GetAllByPermission(BaselineTemplate, workspace, org_id=query.org_id).get_filter()
        
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'title':
                filter_params.append(BaselineTemplate.title.like(f'%{value}%'))
            elif key == 'group_id':
                filter_params.append(BaselineTemplate.group_id == value)
                filter_params.append(BaselineTemplate.permission_type == 'group')
            elif key == 'org_id':
                filter_params.append(BaselineTemplate.org_id == value)
                filter_params.append(BaselineTemplate.permission_type == 'org')
        if hasattr(g, "user_id"):
            filter_params.append(
                or_(
                    BaselineTemplate.creator_id == g.user_id,
                    BaselineTemplate.openable.is_(True)
                )
            )
        baselinetemps = BaselineTemplate.query.filter(*filter_params).all()
        
        return_data = [baseline_template.to_json() for baseline_template in baselinetemps]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


    @staticmethod
    @collect_sql_error
    def check_enable_inherit_all(baseline_template, inherit_template):
        result = False
        if baseline_template.type == inherit_template.type:
            if (
                baseline_template.type == "org" and \
                baseline_template.org_id == inherit_template.org_id
            ) or (
                baseline_template.type == "group" and \
                baseline_template.group_id == inherit_template.group_id
            ):
                result = True
        return result


    @staticmethod
    @collect_sql_error
    def impl_select_base_node_casenode(baseline_template, base_node):
        _casenode = None
        
        filter_params = [
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
        new_base_node = BaseNode(
            baseline_template_id=baseline_template.id,
            permission_type=base_node.permission_type,
            type=base_node.type,
            title=base_node.title,
            creator_id=g.user_id,
            case_node_id=casenode.id if casenode is not None else None,
            org_id=redis_client.hget(RedisKey.user(g.user_id), 'current_org_id'),
            group_id=base_node.group_id if base_node.type == "group" else None,
            is_root=base_node.is_root
        )
        _id = new_base_node.add_flush_commit_id()
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

        filter_params = [
            BaselineTemplate.id == inherit_baseline_template_id
        ]
        inherit_template = BaselineTemplate.query.filter(*filter_params).first()
        if not inherit_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="inherit_baseline_template does not exist."
            )

        enable_inherit_all = BaselineTemplateHandler.check_enable_inherit_all(
            baseline_template, inherit_template
        )
        if not enable_inherit_all:
            filter_params.append(BaselineTemplate.openable.is_(True))
        inherit_baseline_template = BaselineTemplate.query.filter(*filter_params).first()
        if not inherit_baseline_template:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="inherit_baseline_template does not exist or not openable."
            )
        
        old_root_base_node = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
            BaseNode.is_root == 1,
            ).first()
        if not old_root_base_node:
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = "The root node of baseLineTemplate is empty."
            )

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
                error_msg="baseline_template does not exist"
            )

        parent = BaseNode.query.filter_by(id=body.parent_id).first()
        if not parent:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="parent node does not exist"
            )
        if body.title is not None:
            for child in parent.children:
                if body.title == child.title:
                    return jsonify(
                        error_code=RET.DATA_EXIST_ERR,
                        error_msg=f"Title {body.title}  has already existed."
                    )

        if body.type == "directory":
            base_node = BaseNode(
                creator_id=g.user_id,
                group_id=baseline_template.group_id,
                org_id=baseline_template.org_id,
                baseline_template_id=baseline_template.id,
                permission_type=baseline_template.permission_type,
                type=body.type,
                title=body.title,
                is_root=False
            )
            db.session.add(base_node)
            db.session.commit()
            base_node.parent.append(parent)
            base_node.add_update()
            return jsonify(error_code=RET.OK, error_msg="OK")

        base_body = body.__dict__
        
        _case_node_ids = base_body.pop("case_node_ids")
        #去重
        for child in parent.children:
            if child.case_node_id in _case_node_ids:
                _case_node_ids.remove(child.case_node_id)

        if len(_case_node_ids) > 0:
            base_body.update({
                "creator_id": g.user_id,
                "group_id": baseline_template.group_id,
                "org_id": baseline_template.org_id,
                "baseline_template_id": baseline_template.id,
                "permission_type": baseline_template.permission_type,
                "case_node_ids": _case_node_ids,
            })
            from celeryservice.tasks import resolve_base_node
            resolve_base_node.delay(
                body=base_body
            )

        return jsonify(error_code=RET.OK, error_msg="OK")


    @staticmethod
    @collect_sql_error
    def delete(base_node_id):
        base_node = BaseNode.query.filter_by(id=base_node_id).first()
        if not base_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The base_node does not exist."
            )
        current_org_id = int(
            redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        )
        if current_org_id != base_node.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to delete")
        
        _baseline_id = base_node.baseline_template_id
        db.session.delete(base_node)
        if base_node.type == "baseline" and _baseline_id:
            baseline_template = BaselineTemplate.query.get(id=_baseline_id)
            db.session.delete(baseline_template)

        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(error_code=RET.OK, error_msg="OK")


class BaselineTemplateApplyHandler:
    def __init__(self, case_node_id, baseline_template_id):
        self.baseline_template = BaselineTemplate.query.filter_by(
            id=baseline_template_id,
            openable=1
        ).first()
        if not self.baseline_template:
            raise ValueError("The baseline_template is not openable, cannot apply.")
        
        self.root_casenode = CaseNode.query.filter_by(id=case_node_id).first()
        if not self.root_casenode.baseline:
            raise ValueError("this node is not a baseline")

        self.root_basenode = BaseNode.query.filter(
            BaseNode.baseline_template_id == baseline_template_id,
            BaseNode.is_root == True,
        ).first()

        self.origin_casenodes = CaseNode.query.filter(
            CaseNode.baseline_id == self.root_casenode.baseline.id,
            CaseNode.type != "baseline",
            sqlalchemy.or_(
                CaseNode.type == "suite",
                CaseNode.type == "case",  
            ),
        ).all()

        self._applied_list = []

    @property
    def applied_list(self):
        return self._applied_list

    def check_valid(self):
        baseline = CaseNode.query.filter_by(baseline_id=self.root_casenode.baseline_id).first()
        if not baseline:
            raise ValueError(
                "The baseline is not exist."
            )            

        baseline_template = BaselineTemplate.query.filter_by(
            id=self.root_basenode.baseline_template_id
        ).first()
        if not baseline_template:
            raise ValueError(
                "The baseline_template is not exist."
            )

        if baseline.permission_type == baseline_template.type == "org":
            if baseline.org_id != baseline_template.org_id:
                raise ValueError(
                    "Orgs cannot be applied to each other."
                ) 

        if baseline.permission_type == baseline_template.type == "group":
            if baseline.group_id != baseline_template.group_id:
                raise ValueError(
                    "Groups cannot be applied to each other."        
                )

        if baseline.permission_type != baseline_template.type:
            if baseline.org_id != baseline_template.org_id:
                raise ValueError(
                    "Orgs cannot be applied to each other."
                )

    def apply(self):
        self._apply(self.root_basenode, self.root_casenode)
    
    def _copy_basenode2casenode(self, from_basenode, to_casenode):
        new_node = CaseNode(
            type=from_basenode.type,
            title=from_basenode.title,
            in_set=False,
            is_root=False,
            group_id=to_casenode.group_id,
            org_id=to_casenode.org_id,
            permission_type=to_casenode.permission_type,
            baseline_id=to_casenode.baseline_id,
            creator_id=g.user_id,
            suite_id=from_basenode.case_node.suite_id if from_basenode.case_node else None,
            case_id=from_basenode.case_node.case_id if from_basenode.case_node else None,
        )
        new_node.add_update()
        
        to_casenode.children.append(new_node)
        to_casenode.add_update()

        self._applied_list.append(new_node.id)
        return new_node

    def _apply_directory(self, from_basenode, to_casenode):
        origin_dirs = dict()
        if to_casenode.children:
            for child in to_casenode.children:
                if child.type == 'directory':
                    origin_dirs[child.title] = child

        if from_basenode.title in origin_dirs.keys():
            return origin_dirs.get(from_basenode.title)
        
        return self._copy_basenode2casenode(from_basenode, to_casenode)
        
    def _apply_suite(self, from_basenode, to_casenode):
        origin_suites = dict()
        if to_casenode.children:
            for child in to_casenode.children:
                if child.type == 'suite':
                    origin_suites[child.suite_id] = child
        
        if from_basenode.case_node.suite_id in origin_suites.keys():
            return origin_suites.get(from_basenode.case_node.suite_id)
        
        return self._copy_basenode2casenode(from_basenode, to_casenode)

    def _apply_case(self, from_basenode, to_casenode):
        origin_cases = dict()
        if to_casenode.children:
            for child in to_casenode.children:
                if child.type == 'case':
                    origin_cases[child.case_id] = child
        
        if from_basenode.case_node.case_id in origin_cases.keys():
            return origin_cases.get(from_basenode.case_node.case_id)
        
        return self._copy_basenode2casenode(from_basenode, to_casenode)
        
    def _apply(self, from_basenode, to_casenode):
        if not from_basenode.children:
            return

        for child in from_basenode.children:
            new_child = None
            if child.type == 'directory':
                new_child = self._apply_directory(child, to_casenode)
            elif child.type == 'suite':
                new_child = self._apply_suite(child, to_casenode)
            elif child.type == 'case':
                new_child = self._apply_case(child, to_casenode)
            
            if new_child:
                self._apply(child, new_child)
