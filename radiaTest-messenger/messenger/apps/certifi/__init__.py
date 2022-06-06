from flask_restful import Api

from .routes import CaCheck


def init_api(api: Api):
    api.add_resource(CaCheck, "/api/v1/ca-check")