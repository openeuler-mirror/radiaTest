from flask_restful import Api

from .routes import UpdateTaskEvent


def init_api(api: Api):
    api.add_resource(UpdateTaskEvent, "/api/v1/openeuler/task/update")