# @Author : lemon-higgins
# @Date   : 2021-09-19 14:54:44
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Desc   :

import logging

from flask import Flask
from flask_restful import Api
import logging
from flask import Flask


def create_app():
    app = Flask(__name__)

    # app.config.from_object("worker.config.settings.Config")
    app.config.from_object("worker.config.settings.DevelopmentConfig")
    # app.config.from_object("worker.config.settings.ProductionConfig")

    logging.basicConfig(
        filename=app.config.get("LOG_PATH"),
        level=app.config.get("LOG_LEVEL"),
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    )

    api = Api(app)

    from worker.apps.vmachine import (
        VmachineEvent,
        VnicEvent,
        VdiskEvent,
        VmachinePower,
        AttachDevice
    )
    from worker.apps.monitor import MonitorEvent

    api.add_resource(VmachineEvent, "/virtual/machine")
    api.add_resource(VmachinePower, "/virtual/machine/power")
    api.add_resource(AttachDevice, "/virtual/machine/attach")
    api.add_resource(VnicEvent, "/virtual/machine/vnic")
    api.add_resource(VdiskEvent, "/virtual/machine/vdisk")
    api.add_resource(MonitorEvent, "/monitor")

    return app
