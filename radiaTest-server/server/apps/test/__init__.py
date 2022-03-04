from flask_restful import Api

from .routes import TestEvent


def init_api(api: Api):
    api.add_resource(TestEvent, "/api/v1/test")
