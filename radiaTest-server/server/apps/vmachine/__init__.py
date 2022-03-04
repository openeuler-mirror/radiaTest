from flask_restful import Api

from .routes import (
    VmachineEvent,
    VnicEvent,
    VdiskEvent,
    VmachineControl,
    AttachDevice,
    VmachineCallbackEvent,
    # VmachineItemEvent
)


def init_api(api: Api):
    api.add_resource(VmachineEvent, "/api/v1/vmachine")
    api.add_resource(VmachineControl, "/api/v1/vmachine/power")
    api.add_resource(AttachDevice, "/api/v1/vmachine/attach")
    api.add_resource(VnicEvent, "/api/v1/vnic")
    api.add_resource(VdiskEvent, "/api/v1/vdisk")
    api.add_resource(VmachineCallbackEvent, "/api/v1/vmachine/callback")
    # api.add_resource(VmachineItemEvent, "/api/v1/vmachine/<int:vmachine_id>")
