# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from celery.utils.log import get_task_logger
from celery.schedules import crontab

from worker import celery
from celeryservice.lib.vmachine import InstallVmachine
from celeryservice.lib.monitor import IllegalMonitor, VmachinesStatusMonitor

__all__ = ['create_vmachine']

logger = get_task_logger(__name__)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute='*/15'),
        async_illegal_monitor.s(),
        name="illegal_monitor"
    )

    sender.add_periodic_task(
        40000.0,
        async_vmachines_status_monitor.s(),
        name="vmachines_status_monitor"
    )


@celery.task
def async_illegal_monitor():
    IllegalMonitor(logger).main()


@celery.task(bind=True)
def create_vmachine(self, auth, body):
    installer = InstallVmachine(logger, auth, body)

    if body.get("method") == "auto":
        installer.kickstart(self)
    elif body.get("method") == "import":
        installer.import_type(self)
    elif body.get("method") == "cdrom":
        installer.cd_rom(self)
    else:
        raise ValueError("unsupported create method")


@celery.task
def async_vmachines_status_monitor():
    VmachinesStatusMonitor(logger).main()
