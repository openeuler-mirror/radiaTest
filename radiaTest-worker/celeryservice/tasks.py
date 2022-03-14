import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from celery.utils.log import get_task_logger
from celery.schedules import crontab

from worker import celery
from .lib.vmachine import InstallVmachine
from .lib.monitor import IllegalMonitor

__all__ = ['create_vmachine']

logger = get_task_logger(__name__)

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute='*/15'), 
        async_illegal_monitor.s(), 
        name="illegal_monitor"
    )

@celery.task
def async_illegal_monitor():
    IllegalMonitor(logger).main()

@celery.task(bind=True)
def create_vmachine(self, body):
    if body.get("method") == "auto":
        InstallVmachine(logger, body).kickstart(self)
    elif body.get("method") == "import":
        InstallVmachine(logger, body)._import(self)
    elif body.get("method") == "cdrom":
        InstallVmachine(logger,body).cd_rom(self)
    else:
        raise ValueError("unsupported create method")