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
# 用例管理(Testcase)相关接口的handler层

import math
import os
import json
import shutil
import time
import datetime
import uuid
import openpyxl
import pytz

from flask import jsonify, g, current_app, request
from sqlalchemy import func
import sqlalchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.db import Insert, Delete, collect_sql_error
from server.utils.page_util import PageUtil
from server.utils.permission_utils import GetAllByPermission
from server.model.testcase import (
    CaseNode, 
    Suite, 
    Case,
    Commit, 
    CaseDetailHistory, 
    CommitComment, 
    SuiteDocument
)
from server.model.framework import GitRepo
from server.model.task import Task, TaskMilestone, TaskManualCase
from server.model.celerytask import CeleryTask
from server.model.message import Message, MsgType, MsgLevel
from server.model.user import User
from server.model.milestone import Milestone
from server.model.job import Analyzed
from server.schema.base import PageBaseSchema
from server.schema.testcase import (
    CaseNodeBaseSchema, 
    AddCaseCommitSchema,
    UpdateCaseCommitSchema, 
    CommitQuerySchema, 
    CaseCommitBatch,
    QueryHistorySchema, 
    CaseNodeBodySchema
)
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.utils.file_util import MarkdownImportFile, ZipImportFile, ExcelImportFile
from server.utils.sheet import Excel
from server.utils.permission_utils import GetAllByPermission
from server.utils.md_util import MdUtil
from celeryservice.tasks import resolve_testcase_file, resolve_testcase_set


class CaseImportHandler:
    CONVERT_METHOD = {
        "md": MdUtil.df2md,
        "xlsx": MdUtil.md2wb,
    }
    
    def __init__(self, file):
        try:
            try:
                self.case_file = ExcelImportFile(file)
            except TypeError:
                self.case_file = MarkdownImportFile(file)
            
            if self.case_file.filetype:
                self.case_file.file_save(
                    current_app.config.get("TMP_FILE_SAVE_PATH")
                )
            else:
                mesg = "Filetype of {}.{} is not supported".format(
                        self.case_file.filename,
                        self.case_file.filetype,
                    )
                raise RuntimeError(mesg)
        
        except RuntimeError as e:
            current_app.logger.error(str(e))
            if os.path.exists(self.case_file.filepath):
                self.case_file.file_remove()
            raise e

    def import_case(self, group_id=None, case_node_id=None):
        permission_type = "org"
        if group_id:
            try:
                _ = int(group_id)
                permission_type = "group"
            except (ValueError, TypeError):
                group_id = None
        else:
            group_id = None

        _task = resolve_testcase_file.delay(
            self.case_file.filepath,
            CeleryTaskUserInfoSchema(
                auth=request.headers.get("authorization"),
                user_id=int(g.gitee_id),
                group_id=group_id,
                org_id=redis_client.hget(
                    RedisKey.user(g.gitee_id),
                    'current_org_id'
                ),
                permission_type=permission_type,
            ).__dict__,
            case_node_id
        )

        if not _task:
            return jsonify(
                error_code=RET.SERVER_ERR, 
                error_msg="could not send task to resolve file"
            )

        _ = Insert(
            CeleryTask,
            {
                "tid": _task.task_id,
                "status": "PENDING",
                "object_type": "testcase_resolve",
                "description": f"resolve testcase {self.case_file.filepath}",
                "user_id": int(g.gitee_id)
            }
        ).single(CeleryTask, '/celerytask')

        return jsonify(error_code=RET.OK, error_msg="OK")

    def convert(self, to=None):
        """convert md => xlsx or xlsx => md

        Args:
            to (str): the target filetype to transfer
        
        Return:
            filepath (str): the convert file save path 

        """
        try:                       
            if to == "md":
                kwargs = {
                    "df": Excel(self.case_file.filetype).load(self.case_file.filepath),
                    "md_path": "{}{}.md".format(
                        current_app.config.get("TMP_FILE_SAVE_PATH"),
                        self.case_file.filename,
                    )
                }
            elif to == "xlsx":
                with open(self.case_file.filepath, "r") as f:
                    _wb_path = "{}{}.xlsx".format(
                        current_app.config.get("TMP_FILE_SAVE_PATH"),
                        self.case_file.filename,
                    )

                    kwargs = {
                        "md_content": f.read(), 
                        "wb_path": _wb_path,
                        "sheet_name": self.case_file.filename,
                    }
                
                wb = openpyxl.Workbook()
                wb.create_sheet(self.case_file.filename)
                wb.save(_wb_path)
            
            return self.CONVERT_METHOD[to](**kwargs)

        except KeyError as e:
            current_app.logger.error(str(e))
            raise RuntimeError(f"convert to {to} is not supported") from e


class CaseNodeHandler:
    @staticmethod
    @collect_sql_error
    def get(case_node_id, query):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="case_node does not exists"
            )

        filter_params = GetAllByPermission(CaseNode).get_filter()
        return_data = CaseNodeBaseSchema(**case_node.__dict__).dict()
        filter_params.append(CaseNode.parent.contains(case_node))
        if query.title:
            filter_params.append(CaseNode.title.like(f'%{query.title}%'))
        
        children = CaseNode.query.filter(*filter_params).all()

        return_data["children"] = [child.to_json() for child in children]

        source = list()
        cur = case_node
        while cur:
            if not cur.parent.all():
                source.append(cur.id)
                break
            if len(cur.parent.all()) > 1:
                raise RuntimeError(
                    "case_node should not have parents beyond one")

            source.append(cur.id)
            cur = cur.parent[0]

        return_data["source"] = source
        if case_node.type == 'case' and source:
            case_result = CaseNodeHandler.get_case_result(case_node.case_id, source[1])
            return_data["result"] = case_result
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_case_result(case_id, root_case_node_id):
        case_result = None
        case = Case.query.get(case_id)
        task = Task.query.filter_by(case_node_id=root_case_node_id, is_delete=False).order_by(
            Task.create_time.desc()).first()
        if task and not task.is_manage_task:
            task_milestone = TaskMilestone.query.filter(
                TaskMilestone.task_id == task.id,
                TaskMilestone.cases.contains(case)
            ).first()
            if case.usabled:
                case_result = task_milestone.job_result
                if task_milestone.job_result == 'block':
                    case_result = 'failed'
                elif task_milestone.job_result == 'done':
                    case_result = 'success'
                analyzed = Analyzed.query.filter_by(job_id=task_milestone.job_id, case_id=case.id).first()
                if analyzed:
                    case_result = analyzed.result if analyzed.result else case_result
            else:
                case_result = 'running'
                manual_case = TaskManualCase.query.filter_by(task_milestone_id=task_milestone.id,
                                                             case_id=case.id).first()
                if manual_case:
                    case_result = manual_case.case_result
        return case_result

    @staticmethod
    @collect_sql_error
    def get_roots(query):
        filter_params = GetAllByPermission(CaseNode).get_filter()
        filter_params.append(CaseNode.is_root.is_(True))
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'title':
                filter_params.append(CaseNode.title.like(f'%{value}%'))
            if key == 'group_id':
                filter_params.append(CaseNode.group_id == value)
                filter_params.append(CaseNode.permission_type == 'group')
            if key == 'org_id':
                filter_params.append(CaseNode.org_id == value)
                filter_params.append(CaseNode.permission_type == 'org')
        case_nodes = CaseNode.query.filter(*filter_params).all()
        return_data = [case_node.to_json() for case_node in case_nodes]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__
        _body.update({"creator_id": g.gitee_id})
        _body.update({"org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')})
        if not body.parent_id:
            case_node_id = Insert(CaseNode, body.__dict__).insert_id()
            return jsonify(error_code=RET.OK, error_msg="OK", data=case_node_id)

        parent = CaseNode.query.filter_by(id=body.parent_id).first()
        if not parent:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="parent node does not exist")
        root_case_node = CaseNodeHandler.get_root_case_node(body.parent_id)
        task = Task.query.filter(
            Task.case_node_id == root_case_node.id,
            Task.accomplish_time.is_(None),
            Task.is_delete.is_(False),
            Task.is_manage_task.is_(False),
            ).first()
        if task:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg="task exists,not allowed to create a new directory/suite"
            )

        if root_case_node.type == "baseline":
            _body.update({"baseline_id": root_case_node.baseline_id})

        for child in parent.children:
            if _body["title"] == child.title:
                return jsonify(
                    error_code=RET.OK,
                    error_msg="Title {} is already exist".format(
                        _body["title"]
                    ),
                    data=child.id
                )
        
        case_node = CaseNode.query.filter_by(
            id=Insert(
                CaseNode,
                _body,
            ).insert_id()
        ).first()

        case_node.parent.append(parent)
        case_node.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK", data=case_node.id)

    @staticmethod
    @collect_sql_error
    def update(case_node_id, body):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()

        current_org_id = int(
            redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        )

        if current_org_id != case_node.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to edit")

        if not case_node:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="case_node does not exist")

        case_node.title = body.title

        case_node.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(case_node_id):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="case_node does not exist")

        current_org_id = int(
            redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        )

        if current_org_id != case_node.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to delete")
        
        db.session.delete(case_node)

        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def import_case_set(file, group_id):
        uncompressed_filepath = None
        try:
            zip_case_set = ZipImportFile(file)

            if zip_case_set.filetype:
                zip_case_set.file_save(
                    current_app.config.get("TMP_FILE_SAVE_PATH")
                )

                uncompressed_filepath = "{}/{}".format(
                    os.path.dirname(zip_case_set.filepath),
                    zip_case_set.filename
                )

                zip_case_set.uncompress(os.path.dirname(zip_case_set.filepath))

                permission_type = "org"
                if group_id:
                    try:
                        _ = int(group_id)
                        permission_type = "group"
                    except (ValueError, TypeError):
                        group_id = None
                else:
                    group_id = None

                _task = resolve_testcase_set.delay(
                    zip_case_set.filepath,
                    uncompressed_filepath,
                    CeleryTaskUserInfoSchema(
                        auth=request.headers.get("authorization"),
                        user_id=int(g.gitee_id),
                        group_id=group_id,
                        org_id=redis_client.hget(
                            RedisKey.user(g.gitee_id),
                            'current_org_id'
                        ),
                        permission_type=permission_type,
                    ).__dict__,
                )

                _ = Insert(
                    CeleryTask,
                    {
                        "tid": _task.task_id,
                        "status": "PENDING",
                        "object_type": "caseset_resolve",
                        "description": "Import a set of testcases",
                        "user_id": int(g.gitee_id)
                    }
                ).single(CeleryTask, '/celerytask')

                return jsonify(error_code=RET.OK, error_msg="OK")

            else:
                if os.path.exists(zip_case_set.filepath):
                    zip_case_set.file_remove()
                if uncompressed_filepath and os.path.exists(uncompressed_filepath):
                    shutil.rmtree(uncompressed_filepath)

                return jsonify(error_code=RET.FILE_ERR, error_msg="filetype is not supported")

        except RuntimeError as e:
            current_app.logger.error(str(e))

            if os.path.exists(zip_case_set.filepath):
                zip_case_set.file_remove()
            if uncompressed_filepath and os.path.exists(uncompressed_filepath):
                shutil.rmtree(uncompressed_filepath)

            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))

    @staticmethod
    @collect_sql_error
    def get_all_suite(case_node_id):
        _case_node = CaseNode.query.get(case_node_id)
        res_ids = []
        res_items = []

        def get_children(case_node: CaseNode):
            if case_node.type != 'suite' and case_node.type != "case":
                children = CaseNode.query.filter(CaseNode.parent.contains(case_node)).all()
                for child in children:
                    get_children(child)
            elif case_node.type == "suite":
                res_ids.append(case_node.suite_id)
                res_items.append(Suite.query.get(case_node.suite_id))

        if _case_node:
            get_children(_case_node)
        return res_ids, res_items

    @staticmethod
    @collect_sql_error
    def get_all_case(case_node_id):
        _case_node = CaseNode.query.get(case_node_id)
        res_ids = []
        res_items = []

        def get_children(case_node: CaseNode):
            if case_node.type != 'case':
                children = CaseNode.query.filter(CaseNode.parent.contains(case_node)).all()
                for child in children:
                    get_children(child)
            else:
                res_ids.append(case_node.case_id)
                res_items.append(Case.query.get(case_node.case_id))

        if _case_node:
            get_children(_case_node)
        return res_ids, res_items

    @staticmethod
    @collect_sql_error
    def get_root_case_node(case_node_id):
        _case_node = CaseNode.query.get(case_node_id)
        root_case_node = []

        def get_parent(case_node: CaseNode):
            if not case_node.is_root:
                parent = CaseNode.query.filter(CaseNode.children.contains(case_node)).first()
                get_parent(parent)
            else:
                root_case_node.append(case_node)

        if _case_node:
            get_parent(_case_node)
        return root_case_node[0]

    @staticmethod
    @collect_sql_error
    def get_caseset_children(_type, _table, _id):
        _item = _table.query.filter_by(id=_id).first()
        if not _item:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"{_type} does not exist",
            )
        
        filter_params = [
            CaseNode.title == "用例集",
            CaseNode.is_root == True,
            CaseNode.type == "directory",
            CaseNode.permission_type == _type,
        ]

        if _type == "org":
            filter_params.append(CaseNode.org_id == _id)
        else:
            filter_params.append(CaseNode.group_id == _id)

        _caseset = CaseNode.query.filter(*filter_params).first()
        if not _caseset:
            return jsonify(
                error_code=RET.OK,
                error_msg="OK",
                data=[]
            )
        
        return_data = [child.to_json() for child in _caseset.children]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=return_data,
        )

    @staticmethod
    @collect_sql_error
    def get_task(case_node_id, res_type=None):
        from server.apps.task.handlers import HandlerTask
        task = Task.query.filter_by(
            case_node_id=case_node_id,
            is_delete=False
        ).order_by(Task.create_time.desc()).first()
        if task:         
            return HandlerTask.get(task.id, res_type=res_type)
        else:
            return None


    @staticmethod
    @collect_sql_error
    def create_relate_case_node(nodes, case_node, parent_id, 
            suite_case_node=None, case_case_node=None):
        flag = False
        if suite_case_node:
            check_suite_case_node = CaseNode.query.filter(
                CaseNode.suite_id == suite_case_node.suite_id,
                CaseNode.type == "suite",
                CaseNode.baseline_id == case_node.baseline_id,
            ).first()      
            if not check_suite_case_node:
                flag = True
                node_body = suite_case_node.to_json() 
            else:
                _id = check_suite_case_node.id
        if case_case_node:
            check_case_case_node = CaseNode.query.filter(
                CaseNode.case_id == case_case_node.case_id,
                CaseNode.type == "case",
                CaseNode.baseline_id == case_node.baseline_id,
            ).first()      
            if not check_case_case_node:
                flag = True
                node_body = case_case_node.to_json()
            else:
                _id = check_case_case_node.id

        if flag:
            if node_body["is_root"] is True:
                    node_body.update({
                        "is_root": False
                    })                         
            node_body.pop("id")
            node_body.update({
                "baseline_id":case_node.baseline_id,
                "creator_id": g.gitee_id,
                "case_node_id": suite_case_node.id if suite_case_node else case_case_node.id,
                "title": suite_case_node.title if suite_case_node else case_case_node.title,
                "milestone_id": case_node.milestone_id,
                "permission_type": case_node.permission_type,
            })
            if case_node.permission_type == "group":
                node_body.update({
                    "group_id": case_node.group_id
            })
            _id = Insert(CaseNode, node_body).insert_id(CaseNode, '/case_node')

            parent = CaseNode.query.filter_by(id=parent_id).first()
            child = CaseNode.query.filter_by(id=_id).first()
            child.parent.append(parent)
            child.add_update() 
        
        nodes.append(_id)
        return _id, nodes

    @staticmethod
    @collect_sql_error
    def relate(case_node_id, body):
        nodes = list()
        case_node = CaseNode.query.filter_by(
            id=case_node_id).first()
        if not case_node:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Case-node is not exist.")
        
        suite_case_node = CaseNode.query.filter(
            CaseNode.suite_id == body.suite_id,
            CaseNode.type == "suite",
            CaseNode.baseline_id.is_(None),
            ).first()
        if not suite_case_node:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="suite_case_node is not exist.")

        resp = CaseNodeHandler.create_relate_case_node(
            nodes, case_node, case_node_id, suite_case_node=suite_case_node
        )
        if type(resp) == tuple:
            suite_id, nodes = resp
        else:
            return resp

        for case_id in body.case_ids:
            case_case_node = CaseNode.query.filter(
                CaseNode.case_id == case_id,
                CaseNode.type == "case",
                CaseNode.baseline_id.is_(None),
                ).first()
            if not case_case_node:
                return jsonify(error_code=RET.NO_DATA_ERR, error_msg="case_case_node is not exist.")

            resp = CaseNodeHandler.create_relate_case_node(
                nodes, case_node, suite_id, case_case_node=case_case_node
            )
            if type(resp) == tuple:
                case_id, nodes = resp
            else:
                return resp
        return jsonify(error_code=RET.OK, error_msg="OK", data=nodes)

    @staticmethod
    @collect_sql_error
    def create_task_with_casenode(case_node, body):
        if case_node.type == 'case':
            body.automatic = True

        from server.apps.task.handlers import HandlerTask
        task = Task.query.filter_by(
            case_node_id=case_node.id,
            is_delete=False
        ).order_by(Task.create_time.desc()).first()
        if not task:
            return HandlerTask.create(body)
        else:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="task of case-node is exist.")

    @staticmethod
    def get_timestamp(date):
        return time.mktime(date.timetuple())

    @staticmethod
    @collect_sql_error
    def get_suite_casenode(baseline_id, case_node_id):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="case-node is not exist.")
        
        filter_params = [
            CaseNode.baseline_id == baseline_id,
            CaseNode.type == "suite",
        ]
        suite_nodes = CaseNode.query.join(Suite).filter(*filter_params).all()

        return suite_nodes
 

    @staticmethod
    @collect_sql_error
    def get_case_node(milestone_id):
        case_nodes = CaseNode.query.filter_by(milestone=milestone_id).all()
        return_data = [CaseNodeHandler.get_case_node_process(case_node) for case_node in case_nodes]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_product_case_node(product_id):
        _filter = [
            Milestone.type == 'update',
            Milestone.product_id == product_id,
            CaseNode.milestone == Milestone.id
        ]
        case_nodes = CaseNode.query.filter(*_filter).all()
        return_data = [CaseNodeHandler.get_case_node_process(case_node) for case_node in case_nodes]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_case_node_process(case_node):
        case_ids, cases = CaseNodeHandler.get_all_case(case_node.id)
        root_case_node = CaseNodeHandler.get_root_case_node(case_node.id)
        success_count = 0
        for case_id in case_ids:
            if CaseNodeHandler.get_case_result(case_id, root_case_node.id) == 'success':
                success_count = success_count + 1
        progress = '0%' if len(cases) == 0 else str(int(float(success_count) / len(cases) * 100)) + '%'
        case_node = case_node.to_json()
        case_node['progress'] = progress
        return case_node


class SuiteHandler:
    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__
        _body.update({"creator_id": g.gitee_id})
        _body.update({"org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')})
        _id = Insert(Suite, _body).insert_id(Suite, "/suite")
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})


class CaseHandler:
    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__

        _suite = Suite.query.filter_by(name=_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )
        _body["suite_id"] = _suite.id
        _body.pop("suite")
        _body.update({"creator_id": g.gitee_id})
        _body.update({"org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')})
        _body.update({"group_id": _suite.group_id})
        _id = Insert(Case, _body).insert_id(Case, "/case")
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})

    @staticmethod
    @collect_sql_error
    def create_case_node_commit(body):
        _body = body.__dict__

        _suite = Suite.query.filter_by(name=_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )
        _body["suite_id"] = _suite.id
        _body.pop("suite")
        _body.update({"creator_id": g.gitee_id})
        _body.update({"org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')})

        _id = Insert(Case, _body).insert_id(Case, "/case")

        _case_node_body = CaseNodeBodySchema(
            case_id=_id,
            group_id=_body.get("group_id"),
            parent_id=_body.get("parent_id"),
            title=_body.get("name"),
            type="case",
            creator_id=g.gitee_id,
            org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'),
        )

        _result = CaseNodeHandler.create(_case_node_body)
        _result = _result.get_json()
        _case_node = CaseNode.query.filter_by(id=_result["data"]).first()
        source = list()
        cur = _case_node

        while cur:
            if not cur.parent.all():
                source.append(cur.id)
                break
            if len(cur.parent.all()) > 1:
                raise RuntimeError(
                    "case_node should not have parents beyond one")

            source.append(cur.id)
            cur = cur.parent[0]

        insert_data = _body
        insert_data['title'] = 'review new testcase ' + _body.get("name")
        insert_data['description'] = 'review new testcase ' + _body.get("name")
        insert_data['version'] = str(uuid.uuid4()).replace('-', '')
        insert_data['case_description'] = _body.get("description")
        insert_data['case_detail_id'] = _id
        insert_data['remark'] = 'review new testcase ' + _body.get("name")
        insert_data['status'] = 'pending'
        insert_data['case_mod_type'] = 'add'
        insert_data['expectation'] = _body.get("expection")

        _source = source
        _source.reverse()
        _source_str = ''
        for _s in _source:
            _source_str += CaseNode.query.get(_s).title + '>'
        _source_str += _body.get("name")
        insert_data['source'] = _source_str
        _ = Insert(Commit, insert_data).insert_id(Commit, '/commit')
        return jsonify(error_code=RET.OK, error_msg="OK")


class TemplateCasesHandler:
    @staticmethod
    @collect_sql_error
    def get_all(git_repo_id):
        _filter = GetAllByPermission(GitRepo).get_filter()
        _gitrepo = GitRepo.query.filter(*_filter).first()
        if not _gitrepo:
            raise RuntimeError("gitrepo does not exist/ has no right")
        suites = Suite.query.join(Case).filter(
            Suite.git_repo_id == git_repo_id
        ).all()
        data = [suite.relate_case_to_json() for suite in suites]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=data,
        )


class HandlerCaseReview(object):
    @staticmethod
    @collect_sql_error
    def create(body: AddCaseCommitSchema):
        """发起"""
        _commit = Commit.query.filter(Commit.case_detail_id == body.case_detail_id,
                                      Commit.creator_id == g.gitee_id,
                                      Commit.status.in_(['pending', 'open'])).first()
        if _commit:
            return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg="has no right")
        insert_data = body.__dict__

        insert_data['status'] = 'pending'
        insert_data['creator_id'] = g.gitee_id
        case = Case.query.get(body.case_detail_id)
        insert_data['permission_type'] = case.permission_type
        insert_data['org_id'] = case.org_id
        insert_data['group_id'] = case.group_id
        insert_data['version'] = str(uuid.uuid4()).replace('-', '')


        _source = body.source
        _source.reverse()
        source = ''
        for _s in _source:
            source += CaseNode.query.get(_s).title + '>'
        source += case.name
        insert_data['source'] = source
        commit_id = Insert(Commit, insert_data).insert_id(Commit, '/commit')
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def send_massage(commit, _commits):
        creator = User.query.get(commit.creator_id)
        for _commit in _commits:
            _commit.status = 'pending'
            _commit.add_update()
            Insert(
                Message,
                {
                    "data": json.dumps(
                        {
                            "info": f'您提交的名为<b>{_commit.title}</b>的用例评审因已合入'
                                    f'<b>{creator.gitee_name}</b>提交版本,故已退回,请知悉'
                        }
                    ),
                    "level": MsgLevel.user.value,
                    "from_id": g.gitee_id,
                    "to_id": _commit.creator_id,
                    "type": MsgType.text.value,
                    "org_id": _commit.org_id
                }
            ).insert_id()

    @staticmethod
    @collect_sql_error
    def update(commit_id, body: UpdateCaseCommitSchema):
        commit = GetAllByPermission(Commit).single({"id": commit_id})
        if not commit:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="commit not exists/has no right")
        if body.open_edit:
            comment = CommitComment(
                content='creator re-edit',
                creator_id=g.gitee_id,
                parent_id=0,
                commit_id=commit.id)
            comment.add_update()

        for key, value in body.dict().items():
            if value and hasattr(commit, key):
                setattr(commit, key, value)
            commit.add_update()

        if body.status == 'accepted':
            commit.reviewer_id = g.gitee_id
            commit.review_time = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
            commits = Commit.query.filter_by(case_detail_id=commit.case_detail_id, status='open').all()
            HandlerCaseReview.send_massage(commit, commits)
            for _commit in commits:
                _commit.status = 'pending'
                _commit.add_update()

            #  存进历史记录表
            case_history = CaseDetailHistory(
                creator_id=commit.creator_id,
                machine_type=commit.machine_type,
                title=commit.title,
                machine_num=commit.machine_num,
                preset=commit.preset,
                case_description=commit.case_description,
                steps=commit.steps,
                expectation=commit.expectation,
                remark=commit.remark,
                version=commit.version,
                commit_id=commit.id,
                case_id=commit.case_detail_id)
            case_history.add_flush_commit()
            case = Case.query.get(commit.case_detail_id)
            if not case:
                return jsonify(error_code=RET.NO_DATA_ERR, error_msg="case not exists")
            case.machine_type = commit.machine_type
            case.machine_num = commit.machine_num
            case.preset = commit.preset
            case.description = commit.case_description
            case.steps = commit.steps
            case.expectation = commit.expectation
            case.remark = commit.remark
            case.version = case_history.version
            case.add_update()
        if body.status == 'rejected':
            commit.reviewer_id = g.gitee_id
            commit.review_time = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
            if commit.case_mod_type == "add":
                _case_node = CaseNode.query.filter_by(case_id=commit.case_detail_id).first()
                db.session.delete(_case_node)
                db.session.commit()
                _case = Case.query.filter_by(id=commit.case_detail_id).first()
                db.session.delete(_case)
                db.session.commit()

        commit.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def update_batch(body: CaseCommitBatch):
        if len(body.commit_ids) == 0:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="No data is selected.")
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        if body.commit_ids:
            for commit_id in body.commit_ids:
                commit = Commit.query.filter_by(id=commit_id, creator_id=g.gitee_id, org_id=org_id).first()
                if not commit:
                    continue
                if commit and commit.status == 'pending':
                    setattr(commit, 'status', 'open')
                    commit.add_update()
        return jsonify(error_code=RET.OK, error_msg='OK')

    @staticmethod
    @collect_sql_error
    def delete(commit_id):
        commit = GetAllByPermission(Commit).single({"id": commit_id})
        if not commit or commit.status == 'pending':
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="commit not exists/not allowed to update")
        db.session.delete(commit)
        db.session.commit()
        if commit.case_mod_type == "add":
            _case_node = CaseNode.query.filter_by(case_id=commit.case_detail_id).first()
            db.session.delete(_case_node)
            db.session.commit()
            _case = Case.query.filter_by(id=commit.case_detail_id).first()
            db.session.delete(_case)
            db.session.commit()
        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def handler_case_detail(commit_id):
        commit = Commit.query.filter_by(id=commit_id).first()
        if not commit:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the commit does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=commit.to_json()
        )

    @staticmethod
    @collect_sql_error
    def handler_get_history(case_id, query: QueryHistorySchema):
        _filter = GetAllByPermission(Commit).get_filter()
        _filter.append(Commit.status == 'accepted')
        _filter.append(Commit.case_detail_id == case_id)
        if query.title:
            _filter.append(Commit.title.like(f'%{query.title}%'))
        if query.start_time:
            _filter.append(Commit.create_time >= query.start_time)
        if query.end_time:
            _filter.append(Commit.create_time <= query.end_time)

        all = Commit.query.filter(*_filter).order_by(Commit.create_time.desc(), Commit.id.asc()).all()
        commit_list = []

        for item in all:
            dict_item = {'commit_id': item.id, 'version': item.version, 'title': item.title}
            commit_list.append(dict_item)
        return jsonify(error_code=RET.OK, error_msg="OK", data=commit_list)

    @staticmethod
    @collect_sql_error
    def handler_get_all(query: CommitQuerySchema):
        query_type_list = ['all', 'open', 'accepted', 'rejected']
        return_data = {}
        _filter = []
        if query.user_type == 'all':
            permission_filter = GetAllByPermission(Commit).get_filter()
            _filter.extend(permission_filter)
        elif query.user_type == 'creator':
            _filter.append(Commit.creator_id == g.gitee_id)
            _filter.append(Commit.org_id == redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'))
        if query.title:
            _filter.append(Commit.title.like(f'%{query.title}%'))

        for query_type in query_type_list:
            type_filter = _filter.copy()
            if query_type == 'all':
                type_filter.append(Commit.status != 'pending')
                all_commits = Commit.query.filter(*type_filter).all()
                return_data['all_count'] = len(all_commits)
                filter_chain = Commit.query.filter(*type_filter).order_by(Commit.create_time.desc(), Commit.id.asc())
                page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size,
                                                      func=lambda x: x.to_json())
                return_data['all_commit'] = page_dict
            else:
                type_filter.append(Commit.status == query_type)
                _commits = Commit.query.filter(*type_filter).all()
                return_data[query_type + '_count'] = len(_commits)
                filter_chain = Commit.query.filter(*type_filter).order_by(Commit.create_time.desc(), Commit.id.asc())
                page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size,
                                                      func=lambda x: x.to_json())
                return_data[query_type + '_commit'] = page_dict

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class HandlerCommitComment(object):
    @staticmethod
    @collect_sql_error
    def add(commit_id, body):
        _body = body.__dict__
        if "content" not in _body.keys() or _body.get("content") == '':
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="no data")
        comment = CommitComment(commit_id=commit_id,
                                content=body.content,
                                parent_id=body.parent_id,
                                creator_id=g.gitee_id,
                                org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'))
        comment.add_update()
        return jsonify(error_code=RET.OK, error_msg='OK')

    @staticmethod
    @collect_sql_error
    def update(comment_id, body):
        _body = body.__dict__
        if "content" not in _body.keys() or _body.get("content") == '':
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="no data")
        comment = CommitComment.query.filter_by(id=comment_id, creator_id=g.gitee_id).first()
        if not comment:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Comment not exist/has no right")
        setattr(comment, 'content', _body.get("content"))
        comment.add_update()
        return jsonify(error_code=RET.OK, error_msg='OK')

    @staticmethod
    def get_comments(commit_id, comment_id, child_list):
        children_comments = CommitComment.query.filter_by(
            commit_id=commit_id,
            parent_id=comment_id).order_by(CommitComment.create_time).all()
        for child in children_comments:
            _comment = child.to_json()
            _child_list = []
            HandlerCommitComment.get_comments(commit_id, child.id, _child_list)
            _comment['child_list'] = _child_list
            child_list.append(_comment)

    @staticmethod
    @collect_sql_error
    def get(commit_id):
        """
        获取评论信息
        @param commit_id:
        @return:
        """
        commit = GetAllByPermission(Commit).single({"id": commit_id})
        if not commit or commit.status == 'pending':
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="commit not exists/has no right")

        # 第一层评论
        comment_list = []
        comments = CommitComment.query.filter_by(commit_id=commit_id, parent_id=0).order_by(
            CommitComment.create_time).all()
        for comment in comments:
            _child_list = []
            HandlerCommitComment.get_comments(commit_id, comment.id, _child_list)
            _comment = comment.to_json()
            _comment['child_list'] = _child_list
            comment_list.append(_comment)
        return jsonify(error_code=RET.OK, error_msg='OK', data=comment_list)

    @staticmethod
    def get_comment_ids(comment_id, id_set):
        children_comments = CommitComment.query.filter_by(
            parent_id=comment_id).order_by(
            CommitComment.create_time).all()
        for child in children_comments:
            if child.id not in id_set:
                id_set.add(child.id)
                HandlerCommitComment.get_comment_ids(child.id, id_set)

    @staticmethod
    @collect_sql_error
    def delete(comment_id):
        comment = CommitComment.query.filter_by(
            id=comment_id,
            creator_id=g.gitee_id,
            org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')).first()
        if not comment:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="Comment not exist/has no right")
        id_set = {comment_id}
        HandlerCommitComment.get_comment_ids(comment_id, id_set)
        Delete(CommitComment, {"id": list(id_set)}).batch()
        return jsonify(error_code=RET.OK, error_msg='OK')

    @staticmethod
    @collect_sql_error
    def get_pending_status(query: PageBaseSchema):
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        filter_chain = Commit.query.filter_by(
            status='pending',
            creator_id=g.gitee_id,
            org_id=org_id).order_by(Commit.create_time.desc(), Commit.id.asc())
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size,
                                              func=lambda x: x.to_json())
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get case commit page error {e}')
        return jsonify(error_code=RET.OK, error_msg='OK', data=page_dict)


class ResourceItemHandler:
    _days_dict = {
        'week': 7,
        'halfMonth': 15,
        'month': 30,
    }

    def __init__(self, commit_type="week", case_node:CaseNode=None, **kwargs):
        if kwargs.get("_type") and kwargs.get("_type") not in ['group', 'org']:
            raise RuntimeError("type error, parameter type must be group or org")
        if (
            kwargs.get("_type") == 'group' and not kwargs.get("group_id")
        ) or (
            kwargs.get("_type") == 'org' and not kwargs.get("org_id")
        ):
            raise RuntimeError("type not match, group_id/org_id not exist")
        if kwargs.get("case_node_type") == 'baseline' and not kwargs.get("baseline_id"):
            raise RuntimeError("baseline id should be offered")

        self._type = kwargs.get("_type")
        self.org_id = kwargs.get("org_id")
        self.group_id = kwargs.get("group_id")
        self.baseline_id = kwargs.get("baseline_id")
        self.case_node_type = kwargs.get("case_node_type")
        self.commit_type = commit_type
        self.case_node = case_node

        
    @staticmethod
    def _transform(data):
        steps = {}
        for (key, value) in data:
            step = {key: value}
            steps.update(step)
        return steps
    
    def _count_accepted_commit(self, _start: datetime.datetime, _end: datetime.datetime):
        _filter_params = self._get_table_filter(Commit)
        _filter_params.extend([
            Commit.review_time.between(_start, _end),
            Commit.status == 'accepted'
        ])
        count_result = Commit.query.filter(*_filter_params).count()
        return count_result

    def _stat_commit(self, start_date: datetime.datetime, period: int):
        total_commit = 0
        date_range = {}
        for i in range(period):
            _date = start_date - datetime.timedelta(days=i)
            _end_of_date = _date + datetime.timedelta(days=1)
            _end_of_date_set_zero = datetime.datetime(
                _end_of_date.year, _end_of_date.month, _end_of_date.day, 
                0, 0, 0
            )
            _commit_count = self._count_accepted_commit(_date, _end_of_date_set_zero)
            
            total_commit += _commit_count
            date_range.update({
                _date.strftime("%Y-%m-%d"): _commit_count
            })
        
        return total_commit, date_range


    def get_case(self):
        cases_filter = self._get_table_filter(Case)
        if self.case_node_type == 'baseline':
            cases_filter.append(CaseNode.baseline_id == self.baseline_id)
        else:
            cases_filter.append(CaseNode.baseline_id == sqlalchemy.null())
        
        all_count = Case.query.join(CaseNode).filter(
            *cases_filter
        ).count()
        auto_count = Case.query.join(CaseNode).filter(
            *cases_filter, 
            Case.automatic.is_(True)
        ).count()

        auto_ratio = '0%'

        if all_count != 0:
            auto_ratio = str(math.floor((auto_count / all_count) * 100)) + '%'

        return all_count, auto_ratio


    def _get_table_filter(self, table): 
        if self._type == 'group':
            table_filter = [
                table.permission_type == 'group',
                table.org_id == int(redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')),
                table.group_id == self.group_id
            ]
        else:
            table_filter = [
                table.permission_type == 'org',
                table.org_id == self.org_id
            ]
        return table_filter


    def get_suite(self):
        suites_filter = self._get_table_filter(Suite)
        if self.case_node_type == 'baseline':
            suites_filter.append(CaseNode.baseline_id == self.baseline_id)
        else:
            suites_filter.append(CaseNode.baseline_id == sqlalchemy.null())
        
        all_count = Suite.query.join(CaseNode).filter(
            *suites_filter,
        ).count()

        return all_count


    def count_children_case(self, node):
        if not node.children:
            return 0
        res = 0
        for child in node.children:
            if child.type == "case":
                res += 1
            else:
                res += self.count_children_case(child)
            
        return res


    def get_case_distribute(self):
        first_children =  list(filter(lambda child:(
            child.type == "directory" or child.type == "suite"
        ), self.case_node.children))
        result = list()

        for first_child in first_children:
            res_first_count = self.count_children_case(first_child)

            result.append({
                "name": first_child.title,
                "value": res_first_count,
            })
            
        return result



    def get_commit(self):
        now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        
        total, distribute = self._stat_commit(
            today, 
            self._days_dict.get(self.commit_type)
        )

        return total, distribute

    def get_commit_attribute(self):
        _filter = [
            Commit.group_id.isnot(None),
            Commit.group_id == self.group_id,
            Commit.status == 'accepted',
            User.gitee_id == Commit.creator_id 
        ]

        commit_attribute = db.session.query(
            User.gitee_name, func.count(Commit.id).label('count') 
        ).filter(*_filter).group_by(Commit.creator_id).all()

        return self._transform(commit_attribute)

    def run(self):
        case_count, auto_ratio = self.get_case()
        suite_count = self.get_suite()
        commit_count, commit_distribute = self.get_commit()
        return_data = {
            "case_count": case_count,
            "auto_ratio": auto_ratio,
            "commit_count": commit_count,            
            "distribute": commit_distribute,
            "suite_count": suite_count,
        }     

        return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=return_data
        )

class CaseSetHandler:
    @staticmethod
    @collect_sql_error
    def get_caseset_details(casenode, case_node_type, query):
        if case_node_type == "directory":
            if casenode.permission_type == "group":
                resource = ResourceItemHandler(
                    _type='group',
                    group_id=casenode.group_id,
                    case_node_type="directory",
                    commit_type=query.commit_type,
                    case_node=casenode,
                )
            if casenode.permission_type == "org":
                resource = ResourceItemHandler(
                    _type='org',
                    org_id=casenode.org_id,
                    case_node_type="directory",
                    commit_type=query.commit_type,
                    case_node=casenode
                )
        
            case_count, auto_ratio = resource.get_case()
            suite_count = resource.get_suite()
            return_commit = resource.get_commit()
            return_data = {
                "case_count": case_count,
                "suite_count": suite_count,
                "auto_ratio": auto_ratio,
                "commit_count":return_commit[0],
                "distribute": return_commit[1],
            }

            type_distribute = resource.get_case_distribute()
            commit_attribute = resource.get_commit_attribute()
            return_data["type_distribute"] = type_distribute
            return_data["commit_attribute"] = commit_attribute
        
        if case_node_type == "baseline":
            if casenode.permission_type == "group":
                resource = ResourceItemHandler(
                    _type='group',
                    group_id=casenode.group_id,
                    case_node_type="baseline",
                    baseline_id=casenode.baseline_id,
                    case_node=casenode,
                )
            if casenode.permission_type == "org":
                resource = ResourceItemHandler(
                    _type='org',
                    org_id=casenode.org_id,
                    case_node_type="baseline",
                    baseline_id=casenode.baseline_id,
                    case_node=casenode,
                )
        
            case_count, auto_ratio = resource.get_case()
            suite_count = resource.get_suite()
            return_commit = resource.get_commit()
            return_data = {
                "case_count": case_count,
                "suite_count": suite_count,
                "auto_ratio": auto_ratio,
                "commit_count": return_commit[0],
                "distribute": return_commit[1],
            }

            type_distribute = resource.get_case_distribute()
            commit_attribute = resource.get_commit_attribute()
            return_data["type_distribute"] = type_distribute
            return_data["commit_attribute"] = commit_attribute
        
        return return_data


class SuiteDocumentHandler:
    @staticmethod
    @collect_sql_error
    def post(suite_id, body):
        _body = body.__dict__
        suites = list()
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The suite is not exist"
            )
        suites.append(suite)
        _body.update({
            "creator_id": g.gitee_id,
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'),
            "group_id": suite.group_id,
            "suite_id": suite_id,
            "permission_type": suite.permission_type,
            }
        )
        _id = Insert(SuiteDocument, _body).insert_id(SuiteDocument, "/suite_document")
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})

