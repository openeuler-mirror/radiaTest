from flask_restful import Api

from .routes import UpdateTaskEvent
from .routes import LoginOrgList
from .routes import VmachineExist

def init_api(api: Api):
    api.add_resource(UpdateTaskEvent, "/api/v1/openeuler/task/update")
    api.add_resource(LoginOrgList, "/api/v1/login/org/list")
    api.add_resource(VmachineExist, "/api/v1/vmachine/check_exist")