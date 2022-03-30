from flask_restful import Api

from .routes import RunSuiteEvent
from .routes import RunTemplateEvent


def init_api(api: Api):
    api.add_resource(RunSuiteEvent, "/api/v1/job/suite")
    api.add_resource(RunTemplateEvent, "/api/v1/job/template")
