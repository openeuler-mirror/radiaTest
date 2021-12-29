from flask_restful import Api

from .routes import UpdateTaskEvent
from .routes import RepoCaseEvent
from .routes import RepoSuiteEvent

def init_api(api: Api):
    api.add_resource(UpdateTaskEvent, "/api/v1/openeuler/task/update")
    api.add_resource(RepoCaseEvent, "/api/v1/repo_monitor/case")
    api.add_resource(RepoSuiteEvent, "/api/v1/repo_monitor/suite")