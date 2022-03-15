from flask_restful import Api

from .routes import TemplateEvent
from .routes import TemplateItemEvent


def init_api(api: Api):
    api.add_resource(TemplateEvent, "/api/v1/template")
    api.add_resource(TemplateItemEvent, "/api/v1/template/<int:template_id>")
