from flask_restful import Api

from messenger.apps.pmachine.routes import (
    Power,
    Install,
    CheckBmcInfo,
    CheckPmachineInfo,
    PmachineSshItem,
    PmachineBmcItem,
    AutoReleaseCheckPmachineEvent,
)


def init_api(api: Api):
    api.add_resource(Power, "/api/v1/pmachine/power")
    api.add_resource(Install, "/api/v1/pmachine/install")
    api.add_resource(CheckBmcInfo, "/api/v1/pmachine/check-bmc-info")
    api.add_resource(CheckPmachineInfo, "/api/v1/pmachine/check-machine-info")
    api.add_resource(PmachineSshItem, "/api/v1/pmachine/ssh")
    api.add_resource(PmachineBmcItem, "/api/v1/pmachine/bmc")
    api.add_resource(AutoReleaseCheckPmachineEvent, "/api/v1/pmachine/auto-release-check")
