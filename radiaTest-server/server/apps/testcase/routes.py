# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-06 20:39:53
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :

import os
from flask import request
from flask.globals import current_app
from flask_restful import Resource
from flask_pydantic import validate
from werkzeug.utils import secure_filename

from server.model.testcase import Suite, Case
from server.utils.db import Insert, Edit, Select, Delete
from server.utils.sheet import Excel, SheetExtractor 
from server.schema.base import DeleteBaseModel, PageBaseSchema
from server.schema.testcase import (
    SuiteBase,
    SuiteUpdate,
    CaseBase,
    CaseUpdate,
)
from server.apps.testcase.handler import CaseFile


class SuiteEvent(Resource):
    @validate()
    def post(self, body: SuiteBase):
        return Insert(Suite, body.__dict__).single(Suite, "/suite")

    @validate()
    def put(self, body: SuiteUpdate):
        return Edit(Suite, body.__dict__).single(Suite, "/suite")

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Suite, body.__dict__).batch(Suite, "/suite")

    def get(self):
        body = request.args.to_dict()
        return Select(Suite, body).fuzz()


class CaseEvent(Resource):
    @validate()
    def post(self, body: CaseBase):
        _body = body.__dict__
        _body["suite_id"] = Suite.query.filter_by(name=_body.get("suite")).first().id
        _body.pop("suite")
        return Insert(Case, _body).single(Case, "/case")

    @validate()
    def put(self, body: CaseUpdate):
        _body = body.__dict__

        if _body["suite"]:
            _body["suite_id"] = Suite.query.filter_by(name=_body.get("suite")).first().id
            _body.pop("suite")

        return Edit(Case, _body).single(Case, "/case")

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Case, body.__dict__).batch(Case, "/case")

    def get(self):
        body = request.args.to_dict()
        return Select(Case, body).precise()


class CaseRecycleBin(Resource):
    def get(self):
        return Select(Case, {"deleted": 1}).precise()


class CaseImport(Resource):
    def post(self):
        case_file = CaseFile(request.form, request.files)

        filetype = case_file.getFiletype()

        if (
            filetype and case_file.checkSuiteValid()
        ):
            file_path = case_file.save(
                current_app.config.get("UPLOAD_FILE_SAVE_PATH")
            )

            cases_data = Excel(filetype).load(file_path)

            cases = SheetExtractor(
                current_app.config.get("OE_QA_TESTCASE_DICT")
            ).run(cases_data)

            for case in cases:
                if case.get("automatic") == '是':
                    case["automatic"] = True
                else:
                    case["automatic"] = False

                _case = Case.query.filter_by(name=case.get("name")).first()
                if not _case:
                    if not case.get("suite"):
                        case["suite"] = case_file.form.get("suite")
                    
                    _suite = Suite.query.filter_by(
                        name=case.get("suite")
                    ).first()

                    if not _suite:
                        Insert(
                            Suite, 
                            {
                                "name": case.get("suite"),
                            }
                        ).single(Suite, '/suite')
                        
                        _suite = Suite.query.filter_by(
                            name=case.get("suite")
                        ).first()

                    case["suite_id"] = _suite.id

                    del case["suite"]

                    Insert(Case, case).single(Case, "/case")

                else:
                    if case.get("suite"):
                        del case["suite"]
                    case["id"] = _case.id

                    Edit(Case, case).single(Case, "/case")

            case_file.remove()
        
            return {'error_code': 200, 'error_message': 'testcase import succeed'}
        else:
            return {'error_code': 30001, 'error_message': 'filetype or suite is invalid'}



        
