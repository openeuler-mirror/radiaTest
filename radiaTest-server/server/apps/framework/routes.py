from flask import request
from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.model.framework import Framework
from server.utils.db import Insert, Delete, Edit, Select
from server.schema.base import DeleteBaseModel
from server.schema.framework import FrameworkBase, FrameworkUpdate


class FrameworkEvent(Resource):
    @validate()
    @response_collect
    @auth.login_required()
    def post(self, body: FrameworkBase):
        return Insert(Framework, body.__dict__).single(Framework, '/framework')

    @validate()
    @response_collect
    @auth.login_required()
    def delete(self, body: DeleteBaseModel):
        return Delete(Framework, body.__dict__).batch(Framework, '/framework')

    @validate()
    @response_collect
    @auth.login_required()
    def put(self, body: FrameworkUpdate):
        return Edit(Framework, body.__dict__).single(Framework, '/framework')

    @response_collect
    @auth.login_required()
    def get(self):
        body = dict()

        for key, value in request.args.to_dict().items():
            if value:
                body[key] = value

        return Select(Framework, body).fuzz()
