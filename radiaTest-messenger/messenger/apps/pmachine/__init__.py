from flask_restful import Api

from .routes import Power
from .routes import Install
from .routes import CheckBmcInfo
from .routes import CheckPmachineInfo


def init_api(api: Api):
    api.add_resource(Power, "/api/v1/pmachine/power")
    api.add_resource(Install, "/api/v1/pmachine/install")
    api.add_resource(CheckBmcInfo, "/api/v1/pmachine/checkbmcinfo")
    api.add_resource(CheckPmachineInfo, "/api/v1/pmachine/checkpmachineinfo")