from flask_restful import Api

from .routes import PmachineEvent, PmachineEventItem
from .routes import Power
from .routes import Install


def init_api(api: Api):
    api.add_resource(PmachineEvent, "/api/v1/pmachine")
    api.add_resource(PmachineEventItem, "/api/v1/pmachine/<int:pmachine_id>")
    api.add_resource(Power, "/api/v1/pmachine/power")
    api.add_resource(Install, "/api/v1/pmachine/install")