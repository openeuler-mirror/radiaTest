import os
from flask import request
from flask.globals import current_app
from flask.json import jsonify
from flask_restful import Resource
from flask_pydantic import validate
from werkzeug.utils import secure_filename

from server.utils.auth_util import auth
from server.utils.response_util import RET, response_collect
from server.model.testcase import Suite, Case
from server.utils.db import Insert, Edit, Select, Delete
from server.utils.sheet import Excel, SheetExtractor 
from server.schema.base import DeleteBaseModel
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
from server.apps.testcase.handler import CaseImportHandler, BaselineHandler


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
            request.form, 
            request.files.get("file")
        )


class SuiteEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: SuiteBase):
        return Insert(Suite, body.__dict__).single(Suite, "/suite")

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
        body = request.args.to_dict()
        return Select(Suite, body).fuzz()


class CaseEvent(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, body: CaseBase):
        _body = body.__dict__

        _suite = Suite.query.filter_by(name=_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR, 
                error_mesg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )
        _body["suite_id"] = _suite.id
        _body.pop("suite")

        return Insert(Case, _body).single(Case, "/case")

    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: CaseUpdate):
        _body = body.__dict__

        if _body["suite"]:
            _body["suite_id"] = Suite.query.filter_by(name=_body.get("suite")).first().id
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
        body = request.args.to_dict()
        return Select(Case, body).precise()


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



        
