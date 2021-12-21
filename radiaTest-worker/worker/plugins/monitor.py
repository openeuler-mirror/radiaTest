# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-07 15:10:30
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :


import abc
import json
import shlex
import requests
import subprocess
from time import sleep


class BaseMonitor:
    def __init__(self, app, interval) -> None:
        self.app = app
        self.interval = interval

    def run(self):
        while True:
            self.main()
            sleep(self.interval)

    @abc.abstractmethod
    def main(self):
        pass


class IllegalMonitor(BaseMonitor):
    def _get_virsh_domains(self):
        exitcode, output = subprocess.getstatusoutput(
            "virsh list --all | sed -n '$d; 1,2!p' | awk '{print $2}'"
        )
        if exitcode == 0:
            return output.splitlines()

        return []


    def _get_vmachines_from_db(self):
        try:
            while True:
                resp = requests.get(
                    "http://{}:{}/api/v1/vmachine".format(
                        self.app.config.get("SERVER_IP"),
                        self.app.config.get("SERVER_PORT"),
                    ),
                    headers=self.app.config.get("HEADERS"),
                )
                if resp.status_code == "200":
                    break

                sleep(self.interval)

            return list(map(lambda x: x["name"], json.loads(resp.text)))
        except:
            return []

    def main(self):
        v_machines = self._get_vmachines_from_db()
        if v_machines:
            domains = self._get_virsh_domains()
            for domain in domains:
                if domain not in v_machines:
                    self.app.logger.warning(
                        domain + " is an illegal vmachine, not established by server"
                    )

                    print("Begin cleaning now......", end="")

                    output = subprocess.getoutput(
                        "sudo virsh destroy {}".format(
                            shlex.quote(domain),
                        )
                    )

                    exitcode, output = subprocess.getstatusoutput(
                        "sudo virsh undefine --nvram --remove-all-storage {}".format(
                            shlex.quote(domain),
                        )
                    )
                    if exitcode != 0:
                        self.app.logger.error(
                            "Error in virsh undefine. Undefine {} failed.".format(
                                shlex.quote(domain),
                            )
                        )

                    print("Complete!")
        else:
            self.app.logger.error(
                "Cannot connect server while illegal monitor is running."
            )
