# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author :
# email :
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)相关接口的init层

from flask_restful import Api

from server.apps.testcase.routes import (
    CaseNodeEvent,
    CaseNodeItemEvent,
    CaseNodeImportEvent,
    OrgSuiteExportEvent,
    SuiteEvent,
    CaseEvent,
    CaseItemEvent,
    CaseNodeCommitEvent,
    CaseImport,
    CaseRecycleBin,
    ResolveTestcaseByFilepath,
    SuiteItemEvent,
    TemplateCasesQuery,
    CaseCommit,
    CaseNodeTask,
    MileStoneCaseNode,
    ProductCaseNode,
    GroupNodeItem,
    OrgNodeItem,
    SuiteDocumentEvent,
    SuiteDocumentItemEvent,
    CaseSetItemEvent,
    BaselineEvent,
    CaseNodeRelateItemEvent,
    GroupCasesetEvent,
    OrgCasesetEvent,
    CaseNodeGetRootEvent,
    CaseNodeMoveToEvent,
    CasefileConvertEvent,
    OrphanOrgSuitesEvent,
    OrphanGroupSuitesEvent,
    CaseNodeSuitesEvent,
    QueryCaseSetNodeEvent,
    CaseEventV2, TestResultEventV2
)


def init_api(api: Api):
    api.add_resource(
        CaseNodeEvent,
        "/api/v1/case-node",
        "/api/v1/ws/<string:workspace>/case-node",
        methods=["POST", "GET"]
    )
    api.add_resource(
        QueryCaseSetNodeEvent,
        "/api/v1/case-set-node",
        methods=["GET"]
    )
    api.add_resource(
        CaseNodeItemEvent,
        "/api/v1/case-node/<int:case_node_id>",
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(
        CaseNodeImportEvent,
        "/api/v1/case-node/case-set",
        methods=["POST", "GET"]
    )
    api.add_resource(
        CaseNodeCommitEvent,
        "/api/v1/case/case-node/commit",
        methods=["POST"]
    )

    api.add_resource(
        CaseNodeRelateItemEvent,
        "/api/v1/case-node/<int:case_node_id>/relate",
        methods=["POST"]
    )
    api.add_resource(
        CaseSetItemEvent, 
        "/api/v1/case-node/<int:case_node_id>/resource",
        methods=["GET"]
    )
    api.add_resource(
        CaseNodeGetRootEvent, 
        "/api/v1/case-node/<int:case_node_id>/get-root",
        methods=["GET"]
    )
    api.add_resource(
        CaseNodeMoveToEvent, 
        "/api/v1/case-node/<int:from_id>/move-to/<int:to_id>",
        methods=["PUT"]
    )
    api.add_resource(
        BaselineEvent,
        "/api/v1/baseline",
        methods=["GET", "POST"]
    )
    api.add_resource(
        SuiteItemEvent, 
        "/api/v1/suite/<int:suite_id>", 
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(
        SuiteEvent, 
        "/api/v1/suite",
        "/api/v1/ws/<string:workspace>/suite",
        methods=["POST", "GET"]
    )
    api.add_resource(
        OrphanOrgSuitesEvent,
        "/api/v1/org/orphan-suites",
        methods=["GET"],
    )
    api.add_resource(
        OrphanGroupSuitesEvent,
        "/api/v1/group/<int:group_id>/orphan-suites",
        methods=["GET"],
    )
    api.add_resource(
        CaseNodeSuitesEvent,
        "/api/v1/case-node/<int:case_node_id>/suites",
        methods=["POST"],
    )
    api.add_resource(
        CaseEvent, 
        "/api/v1/case",
        "/api/v1/ws/<string:workspace>/case",
        methods=["POST", "GET"],
    )
    api.add_resource(
        CaseItemEvent, 
        "/api/v1/case/<int:case_id>", 
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(CaseImport, "/api/v1/case/import", methods=["POST"])
    api.add_resource(
        CaseRecycleBin, 
        "/api/v1/case/recycle-bin",
        "/api/v1/ws/<string:workspace>/case/recycle-bin",  
        methods=["GET"]
    )
    api.add_resource(
        ResolveTestcaseByFilepath, 
        "/api/v1/testcase/resolve-by-filepath",
        methods=["POST"]
    )
    api.add_resource(
        TemplateCasesQuery, 
        "/api/v1/template/cases/<int:git_repo_id>",
        methods=["GET"]
    )
    api.add_resource(CaseCommit,
                     '/api/v1/case/commit',
                     '/api/v1/case/commit/<int:commit_id>',
                     endpoint='commit',
                     methods=["POST"]
                     )

    api.add_resource(
        CaseNodeTask, 
        '/api/v1/case-node/<int:case_node_id>/task', 
        endpoint='case_node_task',
        methods=["GET"]
    )
    api.add_resource(
        MileStoneCaseNode, 
        "/api/v1/milestone/<int:milestone_id>/case-node",
        methods=["GET"]
    )
    api.add_resource(
        ProductCaseNode, 
        "/api/v1/product/<int:product_id>/case-node",
        methods=["GET"]
    )
    api.add_resource(
        GroupNodeItem,
        "/api/v1/group/<int:group_id>/resource",
        methods=["GET"]
    )
    api.add_resource(
        OrgNodeItem,
        "/api/v1/org/<int:org_id>/resource",
        methods=["GET"]
    )
    api.add_resource(
        SuiteDocumentEvent, 
        "/api/v1/suite/<int:suite_id>/document",
        methods=["POST", "GET"]
    )
    api.add_resource(
        SuiteDocumentItemEvent,
        "/api/v1/suite-document/<int:document_id>",
        methods=["GET", "PUT", "DELETE"]
    )
    api.add_resource(
        GroupCasesetEvent,
        "/api/v1/group/<int:group_id>/caseset",
        methods=["GET"]
    )
    api.add_resource(
        OrgCasesetEvent,
        "/api/v1/org/<int:org_id>/caseset",
        methods=["GET"]
    )
    api.add_resource(
        CasefileConvertEvent,
        "/api/v1/casefile/convert",
    )
    api.add_resource(
        OrgSuiteExportEvent,
        "/api/v1/org/<int:org_id>/case-node/<int:case_node_id>/export",
    )
    api.add_resource(
        CaseEventV2,
        "/api/v1/ws/<string:workspace>/caseV2",
    )
    api.add_resource(
        TestResultEventV2,
        "/api/v1/testcase/test-result",
    )
