from flask import request, g
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.model.job import Analyzed, Job
from server.utils.db import Edit, Select
from server.schema.job import RunSuiteBase, RunTemplateBase, AnalyzedUpdate, NewRunSuiteBase, NewRunTemplateBase
from server.apps.job.handlers import RunSuite, RunTemplate
from server.model.testcase import Case
from server.utils.auth_util import auth
from server.utils.response_util import RET
from celeryservice.tasks import run_suite, run_template


class RunSuiteEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: RunSuiteBase):
        return RunSuite(body.__dict__).run()


class RunTemplateEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: RunTemplateBase):
        return RunTemplate(body.__dict__).run()


class NewRunSuiteEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: NewRunSuiteBase):
        _body = body.__dict__
        _user = {
            "user_id": int(g.gitee_id),
            "auth": request.headers.get("authorization"),
        }
        run_suite.delay(_body, _user)
        return jsonify(error_code=RET.OK, error_msg="succeed in creating the job for running suite")


class NewRunTemplateEvent(Resource):
    @auth.login_required
    @validate()
    def post(self, body: NewRunTemplateBase):
        _body = body.__dict__
        _user = {
            "user_id": int(g.gitee_id),
            "auth": request.headers.get("authorization"),
        }
        run_template.delay(_body, _user)
        return jsonify(error_code=RET.OK, error_msg="succeed in creating the job for running template")


class JobEvent(Resource):
    @auth.login_required
    def get(self):
        body = request.args.to_dict()
        return Select(Job, body).fuzz()


class AnalyzedEvent(Resource):
    @auth.login_required
    def get(self):
        body = request.args.to_dict()
        return Select(Analyzed, body).precise()

    @auth.login_required
    @validate()
    def put(self, body: AnalyzedUpdate):
        return Edit(Analyzed, body.__dict__).single(Analyzed, '/analyzed')


class AnalyzedRecords(Resource):
    @auth.login_required
    def get(self):
        body = request.args.to_dict()

        if not body.get("case"):
            return {"error_code": RET.NO_KEYS_ERR, "error_msg": "validation_error"}

        _case = Case.query.filter_by(name=body.get("case")).first()

        if not _case:
            return {"error_code": RET.NO_RECORDS_ERR, "error_msg": "case is not exist"}

        return Select(Analyzed, {"case_id": _case.id}).precise()


class AnalyzedLogs(Resource):
    @auth.login_required
    def get(self):
        body = request.args.to_dict()

        if not body.get("id"):
            return {"error_code": RET.NO_KEYS_ERR, "error_msg": "validation_error"}
        
        _analyzed = Analyzed.query.filter_by(id=body.get("id")).first()

        return jsonify(_analyzed.get_logs())
