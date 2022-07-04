from flask_restful import Api

from .routes import (
    VmachineEvent,
    VnicEvent,
    VdiskEvent,
    VmachineControl,
    AttachDevice,
    VmachineItemEvent,
	VmachineDelayEvent,
    VmachineBatchDelayEvent,
    VmachineItemForceEvent,
    VmachineData,
    VmachineItemData,
    VnicData,
    VnicItemData,
    VdiskData,
    VdiskItemData,
    PreciseVmachineEvent,
    VmachineIpaddrItem,
    VmachineSshEvent
)


def init_api(api: Api):
    api.add_resource(VmachineEvent, "/api/v1/vmachine")
    api.add_resource(PreciseVmachineEvent, "/api/v1/vmachine/preciseget")
    api.add_resource(VmachineBatchDelayEvent, "/api/v1/vmachine/batchdelay")
    api.add_resource(VmachineItemForceEvent, "/api/v1/vmachine/<int:vmachine_id>/force")
    api.add_resource(VmachineDelayEvent, "/api/v1/vmachine/<int:vmachine_id>/delay")
    api.add_resource(VmachineIpaddrItem, "/api/v1/vmachine/<int:vmachine_id>/ipaddr")
    api.add_resource(VmachineSshEvent, "/api/v1/vmachine/<int:vmachine_id>/ssh")
    api.add_resource(VmachineItemEvent, "/api/v1/vmachine/<int:vmachine_id>")
    api.add_resource(VmachineControl, "/api/v1/vmachine/power")
    api.add_resource(AttachDevice, "/api/v1/vmachine/attach")
    api.add_resource(VnicEvent, "/api/v1/vnic")
    api.add_resource(VdiskEvent, "/api/v1/vdisk")
    api.add_resource(VmachineData, "/api/v1/vmachine/data")
    api.add_resource(VmachineItemData, "/api/v1/vmachine/<int:vmachine_id>/data")
    api.add_resource(VnicData, "/api/v1/vnic/data")
    api.add_resource(VnicItemData, "/api/v1/vnic/<int:vnic_id>/data")
    api.add_resource(VdiskData, "/api/v1/vdisk/data")
    api.add_resource(VdiskItemData, "/api/v1/vdisk/<int:vdisk_id>/data")
