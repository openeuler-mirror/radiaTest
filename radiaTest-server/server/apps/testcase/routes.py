from celeryservice.tasks import resolve_testcase_file_for_baseline
from flask import request, g, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server import redis_client, casbin_enforcer
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect
from server.utils.permission_utils import GetAllByPermission
from server.model.testcase import Suite, Case, CommitComment
from server.utils.db import Insert, Edit, Select, Delete, collect_sql_error
from server.schema.base import DeleteBaseModel, PageBaseSchema
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.schema.testcase import (
    BaselineBodySchema,
    BaselineQuerySchema,
    BaselineItemQuerySchema,
    BaselineUpdateSchema,
    SuiteBase,
    SuiteCreate,
    SuiteUpdate,
    CaseBase,
    CaseCreate,
    CaseBaselineCommitCreate,
    CaseUpdate,
    AddCaseCommitSchema,
    UpdateCaseCommitSchema,
    CommitQuerySchema,
    AddCommitCommentSchema,
    UpdateCommitCommentSchema,
    CaseCommitBatch,
    QueryHistorySchema
)
from server.apps.testcase.handler import (
    CaseImportHandler,
    BaselineHandler,
    SuiteHandler,
    CaseHandler,
    TemplateCasesHandler,
    HandlerCaseReview,
    HandlerCommitComment
)


class BaselineEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: BaselineBodySchema):
        return BaselineHandler.create(body)

    @auth.login_required()
    @response_collect
    @validate()
    def get(self, query: BaselineQuerySchema):
        return BaselineHandler.get_roots(query)


class BaselineItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, baseline_id: int, query: BaselineItemQuerySchema):
        return BaselineHandler.get(baseline_id, query)

    @auth.login_required()
    @response_collect
    def delete(self, baseline_id):
        return BaselineHandler.delete(baseline_id)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, baseline_id, body: BaselineUpdateSchema):
        return BaselineHandler.update(baseline_id, body)


class BaselineImportEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self):
        if not request.form.get("group_id"):
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="the id of group could not be empty as importing case set"
            )

        return BaselineHandler.import_case_set(
            request.files.get("file"),
            request.form.get("group_id"),
        )

    @auth.login_required()
    @response_collect
    def get(self, baseline_id: int):
        return BaselineHandler.get_all_case(baseline_id)


class SuiteItemEvent(Resource):
    @auth.login_required
    @response_collect
    def get(self, suite_id):
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the suite does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=suite.to_json()
        )

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, suite_id, body: SuiteUpdate):
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the suite does not exist"
            )
        _data = body.__dict__
        _data.update({"id": suite_id})
        return Edit(Suite, body.__dict__).single(Suite, "/suite")

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, suite_id):
        return Delete(Suite, {"id": suite_id}).single(Suite, "/suite")


class SuiteEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: SuiteCreate):
        return SuiteHandler.create(body)

    @auth.login_required()
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Suite).fuzz(body)


class PreciseSuiteEvent(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Suite).precise(body)


class PreciseCaseEvent(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return GetAllByPermission(Case).precise(body)

class CaseBaselineCommitEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CaseBaselineCommitCreate):
        return CaseHandler.create_case_baseline_commit(body)

class CaseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CaseCreate):
        return CaseHandler.create(body)

    @auth.login_required()
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value
        return GetAllByPermission(Case).precise(body)

class CaseItemEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, case_id, body: CaseUpdate):
        _body = body.__dict__
        _case = Case.query.filter_by(id=case_id).first()
        if not _case:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the case does not exist"
            )

        if _body["suite"]:
            _body["suite_id"] = Suite.query.filter_by(
                name=_body.get("suite")).first().id
            _body.pop("suite")

        return Edit(Case, _body).single(Case, "/case")

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, case_id):
        return Delete(Case, {"id": case_id}).single(Case, "/case")

    @auth.login_required()
    @response_collect
    def get(self, case_id):
        return GetAllByPermission(Case).precise({"id": case_id})

class TemplateCasesQuery(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def get(self, git_repo_id):
        return TemplateCasesHandler.get_all(git_repo_id)


class CaseRecycleBin(Resource):
    @auth.login_required()
    @response_collect
    def get(self):
        return GetAllByPermission(Case).precise({"deleted": 1})


class CaseImport(Resource):
    @auth.login_required()
    @response_collect
    def post(self):
        if not request.files.get("file"):
            return jsonify(error_code=RET.PARMA_ERR, error_msg="The file being uploaded is not exist")

        if not request.form.get("group_id"):
            return jsonify(error_code=RET.PARMA_ERR, error_msg="The file should be binded to a group")

        return CaseImportHandler.import_case(
            request.files.get("file"),
            request.form.get("group_id"),
        )


class ResolveTestcaseByFilepath(Resource):
    @auth.login_required()
    @response_collect
    @collect_sql_error
    def post(self):
        body = request.json

        _task = resolve_testcase_file_for_baseline.delay(
            body.get("file_id"),
            body.get("filepath"),
            CeleryTaskUserInfoSchema(
                auth=request.headers.get("authorization"),
                user_id=int(g.gitee_id),
                group_id=body.get("group_id"),
                org_id=redis_client.hget(
                    RedisKey.user(g.gitee_id),
                    'current_org_id'
                )
            ).__dict__,
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
    # @casbin_enforcer.enforcer
    def put(self, commit_id, body: UpdateCaseCommitSchema):
        return HandlerCaseReview.update(commit_id, body)

    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
    def get(self, commit_id):
        return HandlerCaseReview.handler_case_detail(commit_id)

    @auth.login_required()
    @response_collect
    # @casbin_enforcer.enforcer
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
    # @casbin_enforcer.enforcer
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
