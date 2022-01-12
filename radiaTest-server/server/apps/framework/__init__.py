from flask_restful import Api

from .routes import FrameworkEvent


def init_api(api: Api):
    api.add_resource(FrameworkEvent, "/api/v1/framework")