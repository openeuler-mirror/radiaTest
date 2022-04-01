from celeryservice.tasks import resolve_testcase_file_for_baseline
from flask import request, g, jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server import redis_client
from server.utils.redis_util import RedisKey
from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect
from server.model.testcase import Suite, Case
from server.utils.db import Edit, Select, Delete, collect_sql_error
from server.schema.base import DeleteBaseModel
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.schema.testcase import (
    BaselineBodySchema,
    BaselineQuerySchema,
    BaselineItemQuerySchema,
    BaselineUpdateSchema,
    SuiteBase,
    SuiteUpdate,
    CaseBase,
    CaseUpdate,
)
from server.apps.testcase.handler import (
    CaseImportHandler,
    BaselineHandler,
    SuiteHandler,
    CaseHandler,
    TemplateCasesHandler
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


class SuiteEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: SuiteBase):
        return SuiteHandler.create(body)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: SuiteUpdate):
        return Edit(Suite, body.__dict__).single(Suite, "/suite")

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Suite, body.__dict__).batch(Suite, "/suite")

    @auth.login_required()
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return Select(Suite, body).fuzz()


class PreciseSuiteEvent(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return Select(Suite, body).precise()


class PreciseCaseEvent(Resource):
    @auth.login_required
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return Select(Case, body).precise()


class CaseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CaseBase):
        return CaseHandler.create(body)

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: CaseUpdate):
        _body = body.__dict__

        if _body["suite"]:
            _body["suite_id"] = Suite.query.filter_by(
                name=_body.get("suite")).first().id
            _body.pop("suite")

        return Edit(Case, _body).single(Case, "/case")

    @auth.login_required()
    @response_collect
    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Case, body.__dict__).batch(Case, "/case")

    @auth.login_required()
    @response_collect
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return Select(Case, body).fuzz()


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
        return Select(Case, {"deleted": 1}).precise()


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
