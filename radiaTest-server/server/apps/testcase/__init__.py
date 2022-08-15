from flask_restful import Api

from .routes import (
    CaseNodeEvent,
    CaseNodeItemEvent,
    CaseNodeImportEvent,
    SuiteEvent,
    CaseEvent,
    CaseItemEvent,
    CaseNodeCommitEvent,
    CaseImport,
    CaseRecycleBin,
    ResolveTestcaseByFilepath,
    SuiteItemEvent,
    TemplateCasesQuery,
    PreciseCaseEvent,
    PreciseSuiteEvent,
    CaseCommit,
    CaseCommitInfo,
    CaseCommitComment,
    CommitStatus,
    CommitHistory,
    CaseNodeTask,
    MileStoneCaseNode,
    ProductCaseNode,
    ChecklistItem,
    ChecklistEvent,
    GroupNodeItem,
    OrgNodeItem
)


def init_api(api: Api):
    api.add_resource(CaseNodeEvent, "/api/v1/case-node")
    api.add_resource(
        CaseNodeItemEvent,
        "/api/v1/case-node/<int:case_node_id>"
    )
    api.add_resource(
        CaseNodeImportEvent,
        "/api/v1/case-node/case-set",
    )
    api.add_resource(
        CaseNodeCommitEvent,
        "/api/v1/case/case-node/commit",
    )
    api.add_resource(PreciseCaseEvent, "/api/v1/case/preciseget")
    api.add_resource(PreciseSuiteEvent, "/api/v1/suite/preciseget")
    api.add_resource(SuiteItemEvent, "/api/v1/suite/<int:suite_id>")
    api.add_resource(SuiteEvent, "/api/v1/suite")
    api.add_resource(CaseEvent, "/api/v1/case")
    api.add_resource(CaseItemEvent, "/api/v1/case/<int:case_id>")
    api.add_resource(CaseImport, "/api/v1/case/import")
    api.add_resource(CaseRecycleBin, "/api/v1/case/recycle-bin")
    api.add_resource(
        ResolveTestcaseByFilepath, "/api/v1/testcase/resolve-by-filepath"
    )
    api.add_resource(
        TemplateCasesQuery, "/api/v1/template/cases/<int:git_repo_id>"
    )
    api.add_resource(CaseCommit, '/api/v1/case/commit', '/api/v1/case/commit/<int:commit_id>', endpoint='commit')
    api.add_resource(CommitHistory, '/api/v1/commit/history/<int:case_id>', endpoint='commit_history')
    api.add_resource(CommitStatus, '/api/v1/case/commit/status', endpoint='commit_status')
    api.add_resource(CaseCommitInfo, '/api/v1/case/commit/query', '/api/v1/case/commit/count/<query_type>', endpoint='commit_query')
    api.add_resource(CaseCommitComment, '/api/v1/case/<int:commit_id>/comment',
                     '/api/v1/commit/comment/<int:comment_id>', endpoint='commit_comment')
    api.add_resource(CaseNodeTask, '/api/v1/case-node/<int:case_node_id>/task', endpoint='case_node_task')
    api.add_resource(MileStoneCaseNode, "/api/v1/milestone/<int:milestone_id>/case-node")
    api.add_resource(ProductCaseNode, "/api/v1/product/<int:product_id>/case-node")
    api.add_resource(
        GroupNodeItem,
        "/api/v1/group/<int:group_id>/resource",
    )
    api.add_resource(
        OrgNodeItem,
        "/api/v1/org/<int:org_id>/resource",
    )
