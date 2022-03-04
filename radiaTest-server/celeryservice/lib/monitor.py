import os
import datetime
import subprocess

import ntplib
from flask import current_app

from server import db
from server.model.vmachine import Vmachine
from celeryservice.lib import TaskHandlerBase



class LifecycleMonitor(TaskHandlerBase):
    def main(self):
        if self._sync_ntp_time():
            self.logger.info("system time has been justified, start to check vmachines")
            self._check_vmachines_lifecycle()
        else:
            raise RuntimeError("could not justify system time")

    def _check_hardware_time(self):
        output = subprocess.getoutput("hwclock")
        hw_time = datetime.datetime.strptime(output[:25], "%Y-%m-%d %H:%M:%S.%f")
        sys_time = datetime.datetime.now()

        timedelta = hw_time - sys_time
        if timedelta.days < 0:
            timedelta = sys_time - hw_time

        if timedelta.seconds > 300:
            return False

        return True

    def _sync_ntp_time(self):
        client = ntplib.NTPClient()
        resp = None
        for host in current_app.config.get("NTP_SERVER"):
            try:
                resp = client.request(host, port="ntp", version=4, timeout=5)
                if resp:
                    break
            except Exception as e:
                pass

        if not resp:
            return self._check_hardware_time()

        ntp_time = resp.tx_time
        _date, _time = str(datetime.datetime.fromtimestamp(ntp_time))[:25].split(" ")

        exitcode = os.system('date -s "{}"'.format(_date + " " + _time))

        return True if exitcode == 0 else self._check_hardware_time()

    def _check_vmachines_lifecycle(self):
        v_machines = Vmachine.query.all()

        for vmachine in v_machines:
            end_time = vmachine.end_time

            if (datetime.datetime.now() > end_time):
                self.logger.info(
                    "vmachine {} is going to be destroyed, with end_time {}".format(
                        vmachine.name, 
                        vmachine.end_time
                    )
                )
                db.session.delete(vmachine)
        
        db.session.commit()
