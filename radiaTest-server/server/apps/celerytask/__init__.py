from flask_restful import Api

from .routes import CeleryTaskEvent


def init_api(api: Api):
    api.add_resource(CeleryTaskEvent, "/api/v1/celerytask")
