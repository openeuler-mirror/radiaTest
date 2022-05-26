import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from celery.utils.log import get_task_logger

from worker import celery
from .lib.monitor import VmStatusMonitor

__all__ = ['async_vmstatus_monitor']

logger = get_task_logger(__name__)

    
@celery.task(bind=True)
def async_vmstatus_monitor(self, auth, body):
    VmStatusMonitor(logger, auth, body).main(self)