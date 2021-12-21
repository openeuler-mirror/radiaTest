from flask_restful import Api

from .routes import TemplateEvent


def init_api(api: Api):
    api.add_resource(TemplateEvent, "/api/v1/template")
