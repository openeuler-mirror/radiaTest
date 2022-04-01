from flask_restful import Api

from .routes import PmachineEvent, PmachineItemEvent
from .routes import Power
from .routes import Install
from .routes import MachineGroupEvent
from .routes import MachineGroupItemEvent
from .routes import MachineGroupHeartbeatEvent


def init_api(api: Api):
    api.add_resource(PmachineEvent, "/api/v1/pmachine")
    api.add_resource(PmachineItemEvent, "/api/v1/pmachine/<int:pmachine_id>")
    api.add_resource(Power, "/api/v1/pmachine/power")
    api.add_resource(Install, "/api/v1/pmachine/install")
    api.add_resource(MachineGroupEvent, "/api/v1/machine_group")
    api.add_resource(MachineGroupItemEvent, "/api/v1/machine_group/<int:machine_group_id>")
    api.add_resource(MachineGroupHeartbeatEvent, "/api/v1/machine_group/heartbeat")