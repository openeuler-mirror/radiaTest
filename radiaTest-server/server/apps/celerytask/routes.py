from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.schema.celerytask import CeleryTaskQuerySchema
from .handler import CeleryTaskHandler


class CeleryTaskEvent(Resource):
    @auth.login_required()
    @validate()
    def get(self, query:CeleryTaskQuerySchema):
        return CeleryTaskHandler.get_all(query)