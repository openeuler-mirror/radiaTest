import json
import shlex
import requests
import subprocess
from time import sleep

from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase

config = celeryconfig.__dict__

class IllegalMonitor(TaskHandlerBase):
    def _get_virsh_domains(self):
        exitcode, output = subprocess.getstatusoutput(
            "virsh list --all | sed -n '$d; 1,2!p' | awk '{print $2}'"
        )
        if exitcode == 0:
            return output.splitlines()

        return []


    def _get_vmachines_from_db(self):
        try:
            times = 0
            while times < 60:
                resp = requests.get(
                    "http://{}:{}/api/v1/vmachine".format(
                        config.get("SERVER_IP"),
                        config.get("SERVER_PORT"),
                    ),
                    headers=config.get("HEADERS"),
                )
                if resp.status_code == 200:
                    break

                sleep(10)
                times += 1

            return list(
                map(
                    lambda x: x["name"], 
                    json.loads(resp.text).get("data")
                )
            )

        except Exception as e:
            self.logger.error(str(e))
            return []
        
    def main(self):
        v_machines = self._get_vmachines_from_db()
        if v_machines:
            domains = self._get_virsh_domains()
            for domain in domains:
                if domain not in v_machines:
                    self.logger.warn(
                        domain + " is an illegal vmachine, not established by server"
                    )

                    exitcode, output = subprocess.getstatusoutput(
                        "sudo virsh destroy {}".format(
                            shlex.quote(domain),
                        )
                    )
                    if exitcode != 0:
                        self.logger.error(
                            "Error in virsh destroy. Destroy {} failed.".format(
                                shlex.quote(domain),
                            )
                        )

                    exitcode, output = subprocess.getstatusoutput(
                        "sudo virsh undefine --nvram --remove-all-storage {}".format(
                            shlex.quote(domain),
                        )
                    )
                    if exitcode != 0:
                        self.logger.error(
                            "Error in virsh undefine. Undefine {} failed.".format(
                                shlex.quote(domain),
                            )
                        )
                    
                    self.logger.info(
                        f"the illegal vmachine {domain} has been deleted."
                    )

        else:
            self.logger.error(
                "Cannot connect server. Have attempted to connect for 60 times"
            )
