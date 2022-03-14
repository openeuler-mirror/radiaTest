from flask_restful import Api

from .routes import JobItemEvent
from .routes import JobEvent
from .routes import AnalyzedEvent
from .routes import AnalyzedItemEvent
from .routes import AnalyzedRecords
from .routes import AnalyzedLogs
from .routes import RunSuiteEvent
from .routes import RunTemplateEvent


def init_api(api: Api):
    api.add_resource(JobEvent, "/api/v1/job")
    api.add_resource(JobItemEvent, "/api/v1/job/<int:job_id>/children")
    api.add_resource(AnalyzedEvent, "/api/v1/analyzed")
    api.add_resource(AnalyzedItemEvent, "/api/v1/analyzed/<int:analyzed_id>")
    api.add_resource(AnalyzedRecords, "/api/v1/analyzed/records")
    api.add_resource(AnalyzedLogs, "/api/v1/analyzed/<int:analyzed_id>/logs")
    api.add_resource(RunSuiteEvent, "/api/v1/job/suite")
    api.add_resource(RunTemplateEvent, "/api/v1/job/template")
