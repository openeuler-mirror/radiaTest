import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from celery import chain, group, chord, Task
from celery.utils.log import get_task_logger

from worker import celery
from .lib.vmachine import InstallVmachine


__all__ = ['create_vmachine']

logger = get_task_logger(__name__)

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
