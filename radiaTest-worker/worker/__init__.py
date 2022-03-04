import logging

from flask import Flask
from flask_restful import Api
import logging
from flask import Flask
from celery import Celery
from celeryservice import celeryconfig

from worker.utils.config_util import loads_config_ini

celery = Celery(
    main=__name__, 
    broker=celeryconfig.broker_url,
    backend=celeryconfig.result_backend,
    task_routes = {
        'celeryservice.tasks.create_vmachine': {
            'queue': 'queue_create_vmachine',
            'routing_key': 'create_vmachine',
            'delivery_mode': 1,
        },
    }
)

def init_celery(app):
    celery.config_from_object(celeryconfig)

def create_app():
    app = Flask(__name__)

    app.config.from_object("worker.config.settings.Config")

    ini_result = loads_config_ini(app)
    if not ini_result:
        raise RuntimeError("There is no valid config files for this flask app.")

    logging.basicConfig(
        filename=app.config.get("LOG_PATH"),
        level=app.config.get("LOG_LEVEL"),
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    )
    
    init_celery(app)

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
