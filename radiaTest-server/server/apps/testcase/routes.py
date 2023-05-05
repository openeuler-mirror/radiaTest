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

from server import redis_client, casbin_enforcer
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect, workspace_error_collect
from server.utils.permission_utils import GetAllByPermission
from server.model.organization import Organization
from server.model.group import Group
from server.model.testcase import Suite, Case, CaseNode, SuiteDocument, Baseline
from server.model.milestone import Milestone
from server.utils.db import Insert, Edit, Delete, collect_sql_error
from server.schema.base import PageBaseSchema
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.schema.testcase import (
    CaseNodeBodySchema,
    CaseNodeQuerySchema,
    CaseNodeItemQuerySchema,
    CaseNodeSuitesCreateSchema,
    CaseNodeUpdateSchema,
    OrphanSuitesQuerySchema,
    SuiteCreate,
    CaseCreate,
    CaseCreateBody,
    CaseNodeCommitCreate,
    AddCaseCommitSchema,
    UpdateCaseCommitSchema,
    CommitQuerySchema,
    AddCommitCommentSchema,
    UpdateCommitCommentSchema,
    CaseCommitBatch,
    QueryHistorySchema,
    SuiteDocumentBodySchema,
    SuiteDocumentUpdateSchema,
    SuiteDocumentQuerySchema,
    BaselineCreateSchema,
    SuiteCreateBody,
    SuiteCaseNodeUpdate,
    CaseCaseNodeUpdate,
    CaseNodeRelateSchema,
    ResourceQuerySchema,
    CaseSetQuerySchema,
)
from server.apps.testcase.handler import (
    CaseImportHandler,
    CaseNodeHandler,
    CaseHandler,
    OrphanSuitesHandler,
    TemplateCasesHandler,
    HandlerCaseReview,
    HandlerCommitComment,
    ResourceItemHandler,
    SuiteDocumentHandler,
    CaseSetHandler,
)
from server.utils.resource_utils import ResourceManager


class CaseNodeEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CaseNodeBodySchema):
        return CaseNodeHandler.create(body)

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    @validate()
    def get(self, workspace: str, query: CaseNodeQuerySchema):
        return CaseNodeHandler.get_roots(query, workspace)


class CaseNodeItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, case_node_id: int, query: CaseNodeItemQuerySchema):
        return CaseNodeHandler.get(case_node_id, query)

    @auth.login_required()
    @response_collect
    def delete(self, case_node_id):
        return CaseNodeHandler.delete(case_node_id)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, case_node_id, body: CaseNodeUpdateSchema):
        return CaseNodeHandler.update(case_node_id, body)


class CaseNodeImportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self):
        return CaseNodeHandler.import_case_set(
            request.files.get("file"),
            request.form.get("group_id"),
        )

    @auth.login_required()
    @response_collect
    def get(self, case_node_id: int):
        return CaseNodeHandler.get_all_case(case_node_id)


class CaseNodeRelateItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, case_node_id, body: CaseNodeRelateSchema):
        return CaseNodeHandler.relate(case_node_id, body)


class SuiteEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: SuiteCreate):
        return_data = dict()
        suite_body = SuiteCreate(**body.__dict__).dict()
        
        suites = Suite.query.filter_by(name=suite_body["name"]).all()
        if suites:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The name of suite {} is already exist".format(
                    suite_body["name"]
                ),
            )

        suite_body.update({"creator_id": g.gitee_id})
        suite_body.update({
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        })
        _id = Insert(Suite, suite_body).insert_id(Suite, "/suite")
        return_data["suite_id"] = _id

        suite_body.update({"suite_id": _id})

        _body = SuiteCreateBody(**suite_body)
        _resp =  CaseNodeHandler.create(_body)
        _resp = json.loads(_resp.data.decode('UTF-8'))
        if _resp.get("error_code") != RET.OK:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="Create case_node error."
            )
        return_data["case_node_id"] = _resp.get("data")
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


    @auth.login_required()
    @response_collect
    @workspace_error_collect
    def get(self, workspace: str):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Suite, workspace).fuzz(body)


class OrphanOrgSuitesEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: OrphanSuitesQuerySchema):
        handler = OrphanSuitesHandler(query)
        handler.add_filters([
            Suite.permission_type == "org",
        ])
        return handler.get_all()


class OrphanGroupSuitesEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
    def post(self, case_node_id, body: CaseNodeSuitesCreateSchema):
        case_node = CaseNode.query.filter_by(id=case_node_id).first()
        if not case_node or not case_node.in_set:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"case node #{case_node_id} does not exist/not valid",
            )
        
        for suite_id in body.suites:
            suite = Suite.query.filter_by(id=suite_id).first()
            if suite:
                suite_case_node = Insert(
                    CaseNode,
                    {
                        "permission_type": body.permission_type,
                        "org_id": body.org_id,
                        "group_id": body.group_id,
                        "title": suite.name,
                        "type": "suite",
                        "is_root": 0,
                        "in_set": 1,
                        "suite_id": suite.id,
                    } 
                ).insert_obj()

                for testcase in suite.case:
                    testcase_node = Insert(
                        CaseNode,
                        {
                            "permission_type": body.permission_type,
                            "org_id": body.org_id,
                            "group_id": body.group_id,
                            "title": testcase.name,
                            "type": "case",
                            "is_root": 0,
                            "in_set": 1,
                            "case_id": testcase.id,
                            "suite_id": suite.id,
                        } 
                    ).insert_obj()
                    suite_case_node.children.append(testcase_node)
                    suite_case_node.add_update()

                case_node.children.append(suite_case_node)
                case_node.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


class SuiteItemEvent(Resource):
    @auth.login_required
    @response_collect
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
    def put(self, suite_id, body: SuiteCaseNodeUpdate):
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the suite does not exist"
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

        if body.name and body.name != suite.name: 
            case_nodes = CaseNode.query.filter(
                CaseNode.suite_id==suite_id,
            ).all()

            if not case_nodes:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="the case_node does not exist"
                )

            return_resp = [
                CaseNodeHandler.update(
                    case_node.id, body
                ) for case_node in case_nodes
            ]

            for resp in return_resp:
                _resp = json.loads(resp.response[0])
                if _resp.get("error_code") != RET.OK:
                    return _resp
            
        return jsonify(error_code=RET.OK, error_msg="OK")


    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, suite_id):
        case_node = CaseNode.query.filter(
            CaseNode.suite_id == suite_id,
            CaseNode.type == "suite",
            CaseNode.baseline_id.is_(None)
            ).first()
        if not case_node:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the case_node does not exist"
            )
        Delete(CaseNode, {"id": case_node.id}).single(CaseNode, "/case_node")
        return Delete(Suite, {"id": suite_id}).single(Suite, "/suite")


class PreciseSuiteEvent(Resource):
    @auth.login_required
    @response_collect
    @workspace_error_collect
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
    def post(self, body: CaseNodeCommitCreate):
        return CaseHandler.create_case_node_commit(body)


class CaseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
        case_body.update({"creator_id": g.gitee_id})
        case_body.update({
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
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
        _resp =  CaseNodeHandler.create(body)
        _resp = json.loads(_resp.data.decode('UTF-8'))
        if _resp.get("error_code") != RET.OK:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="Create case_node error."
            )
        return_data["case_node_id"] = _resp.get("data")
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)
        

    @auth.login_required()
    @response_collect
    @workspace_error_collect
    def get(self, workspace: str):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value
        return GetAllByPermission(Case, workspace).precise(body)



class CaseItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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

        Edit(Case, _body).single(Case, "/case")
        
        if body.name and body.name != _case.name: 
            case_nodes = CaseNode.query.filter(
                CaseNode.case_id == case_id,
            ).all()

            if not case_nodes:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="the case_node does not exist"
                )

            return_resp = [
                CaseNodeHandler.update(
                    case_node.id, body
                ) for case_node in case_nodes
            ]

            for resp in return_resp:
                _resp = json.loads(resp.response[0])
                if _resp.get("error_code") != RET.OK:
                    return _resp
        
        return jsonify(error_code=RET.OK, error_msg="OK")


    @auth.login_required()
    @response_collect
    @validate()
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


    @auth.login_required()
    @response_collect
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
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, git_repo_id):
        return TemplateCasesHandler.get_all(git_repo_id)


class CaseRecycleBin(Resource):
    @auth.login_required()
    @response_collect
    @workspace_error_collect
    def get(self, workspace: str):
        return GetAllByPermission(Case, workspace).precise({"deleted": 1})


class CaseImport(Resource):
    @auth.login_required()
    @response_collect
    def post(self):
        if not request.files.get("file"):
            return jsonify(
                error_code=RET.PARMA_ERR, 
                error_msg="The file being uploaded is not exist"
            )

        try:
            import_handler = CaseImportHandler(request.files.get("file"))
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
    def post(self):
        body = request.json

        permission_type = "org"
        if body.get("group_id"):
            permission_type = "group"

        _task = resolve_testcase_file.delay(
            body.get("filepath"),
            CeleryTaskUserInfoSchema(
                auth=request.headers.get("authorization"),
                user_id=int(g.gitee_id),
                group_id=body.get("group_id"),
                org_id=redis_client.hget(
                    RedisKey.user(g.gitee_id),
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
    def post(self, body: AddCaseCommitSchema):
        """
        发起用例评审
        :return:
        """
        return HandlerCaseReview.create(body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, commit_id, body: UpdateCaseCommitSchema):
        return HandlerCaseReview.update(commit_id, body)

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def get(self, commit_id):
        return HandlerCaseReview.handler_case_detail(commit_id)

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def delete(self, commit_id):
        return HandlerCaseReview.delete(commit_id)


class CommitHistory(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, case_id, query: QueryHistorySchema):
        return HandlerCaseReview.handler_get_history(case_id, query)


class CaseCommitInfo(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: CommitQuerySchema):
        return HandlerCaseReview.handler_get_all(query)


class CaseCommitComment(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, commit_id, body: AddCommitCommentSchema):
        return HandlerCommitComment.add(commit_id, body)

    @auth.login_required()
    @response_collect
    def get(self, commit_id):
        return HandlerCommitComment.get(commit_id)

    @auth.login_required()
    @response_collect
    def delete(self, comment_id):
        return HandlerCommitComment.delete(comment_id)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, comment_id, body: UpdateCommitCommentSchema):
        return HandlerCommitComment.update(comment_id, body)


class CommitStatus(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: PageBaseSchema):
        return HandlerCommitComment.get_pending_status(query)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: CaseCommitBatch):
        """
        用例评审批量提交
        """
        return HandlerCaseReview.update_batch(body)


class CaseNodeTask(Resource):
    @auth.login_required()
    @response_collect
    def get(self, case_node_id):
        return CaseNodeHandler.get_task(case_node_id)


class MileStoneCaseNode(Resource):
    @auth.login_required()
    @response_collect
    def get(self, milestone_id):
        return CaseNodeHandler.get_case_node(milestone_id)


class ProductCaseNode(Resource):
    @auth.login_required()
    @response_collect
    def get(self, product_id):
        return CaseNodeHandler.get_product_case_node(product_id)


class GroupNodeItem(Resource):
    @auth.login_required()
    @response_collect
    @validate()
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
    @auth.login_required()
    @response_collect
    @validate()
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


    @auth.login_required()
    @response_collect
    @validate()
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
    @auth.login_required()
    @response_collect
    @validate()
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
    @auth.login_required()
    @response_collect
    @validate()
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
        old_parent =  CaseNode.query.filter(
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
    @auth.login_required()
    @response_collect
    @validate()
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
            error_code = RET.OK,
            error_msg = "OK",
            data = root_case_node.to_json()
        )


class CaseSetItemEvent(Resource):
    """
        查询baseline以及caseset的resource信息.
        url="/api/v1/case-node/<int:case_node_id>/resource", 
        methods=["GET"]
    """
    @auth.login_required()
    @response_collect
    @validate()
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
        casenode = CaseNode.query.filter_by(id = case_node_id).first()
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
                return  return_data
        elif casenode.type == "directory" and\
                casenode.is_root == 1 and \
                casenode.title == "用例集":
            # 获取用例集details
            return_data = CaseSetHandler.get_caseset_details(
                casenode, "directory", query)
            if isinstance(return_data, Response):
                return  return_data
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
        _baseline = Baseline.query.filter_by(milestone_id=body.milestone_id).first()
        if _baseline:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="baseline associated with milestone has exist."
            )

        baseline_body = BaselineCreateSchema(**body.__dict__).dict()
        
        baseline_body.update({"creator_id": g.gitee_id})
        baseline_body.update({
            "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        })
        _id = Insert(Baseline, baseline_body).insert_id(Baseline, "/baseline")
        return_data["baseline_id"] = _id

        body.baseline_id = _id
        _resp =  CaseNodeHandler.create(body)
        _resp = json.loads(_resp.data.decode('UTF-8'))

        if _resp.get("error_code") != RET.OK:
            return _resp
        return_data["case_node_id"] = _resp.get("data")
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


class OrgCasesetEvent(Resource):
    @auth.login_required()
    @response_collect
    def get(self, org_id):
        return CaseNodeHandler.get_caseset_children("org", Organization, org_id)


class GroupCasesetEvent(Resource):
    @auth.login_required()
    @response_collect
    def get(self, group_id):
        return CaseNodeHandler.get_caseset_children("group", Group, group_id)


class CasefileConvertEvent(Resource):
    @auth.login_required()
    @response_collect
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