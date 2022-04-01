from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.celerytask import CeleryTaskCreateSchema, CeleryTaskQuerySchema
from .handler import CeleryTaskHandler


class CeleryTaskEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: CeleryTaskQuerySchema):
        return CeleryTaskHandler.get_all(query)

    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: CeleryTaskCreateSchema):
        return CeleryTaskHandler.create(body)