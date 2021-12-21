# -*- coding: utf-8 -*-
# @Author : lemon-higgins
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Date   : 2021-11-15 14:18:54


from flask import request
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate

from server.model.job import Analyzed, Job
from server.utils.db import Edit, Select

from server.schema.job import RunSuiteBase, RunTemplateBase, AnalyzedUpdate
from server.apps.job.handlers import RunSuite, RunTemplate
from server.model.testcase import Case


class RunSuiteEvent(Resource):
    @validate()
    def post(self, body: RunSuiteBase):
        return RunSuite(body.__dict__).run()


class RunTemplateEvent(Resource):
    @validate()
    def post(self, body: RunTemplateBase):
        return RunTemplate(body.__dict__).run()


class JobEvent(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(Job, body).fuzz()


class AnalyzedEvent(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(Analyzed, body).precise()

    @validate()
    def put(self, body: AnalyzedUpdate):
        return Edit(Analyzed, body.__dict__).single(Analyzed, '/analyzed')


class AnalyzedRecords(Resource):
    def get(self):
        body = request.args.to_dict()
        
        if not body.get("case"):
            return {"error_code": 60001, "error_mesg": "validation_error"}
        
        _case = Case.query.filter_by(name=body.get("case")).first()

        if not _case:
            return {"error_code": 60002, "error_mesg": "case is not exist"}
        
        return Select(Analyzed, {"case_id": _case.id}).precise()


class AnalyzedLogs(Resource):
     def get(self):
        body = request.args.to_dict()

        if not body.get("id"):
            return {"error_code": 60001, "error_mesg": "validation_error"}
        
        _analyzed = Analyzed.query.filter_by(id=body.get("id")).first()

        return jsonify(_analyzed.get_logs())
 