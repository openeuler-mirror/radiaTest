from flask_restful import Api

from .routes import RunSuiteEvent
from .routes import RunTemplateEvent
from .routes import JobEvent
from .routes import AnalyzedEvent
from .routes import AnalyzedRecords
from .routes import AnalyzedLogs


def init_api(api: Api):
    api.add_resource(RunSuiteEvent, "/api/v1/job/suite")
    api.add_resource(RunTemplateEvent, "/api/v1/job/template", endpoint='run_template_event')
    api.add_resource(JobEvent, "/api/v1/job")
    api.add_resource(AnalyzedEvent, "/api/v1/analyzed")
    api.add_resource(AnalyzedRecords, "/api/v1/analyzed/records")
    api.add_resource(AnalyzedLogs, "/api/v1/analyzed/logs")