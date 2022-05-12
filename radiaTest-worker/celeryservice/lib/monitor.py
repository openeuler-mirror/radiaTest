import json
import shlex
import requests
import subprocess

from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase


class IllegalMonitor(TaskHandlerBase):
    def _get_virsh_domains(self):
        exitcode, output = subprocess.getstatusoutput(
            "virsh list --all | sed -n '$d; 1,2!p' | awk '{print $2}'"
        )
        if exitcode == 0:
            return output.splitlines()

        return []


    def _query_vmachine(self, domain):
        resp = requests.get(
            "{}://{}/api/v1/vmachine/check_exist".format(
                celeryconfig.protocol_to_server,
                celeryconfig.server_addr,
            ),
            params={
                "domain": domain,
            },
            headers=celeryconfig.headers,
        )
        if resp.status_code != 200:
            raise RuntimeError("the worker cannot connect to server")

        try:
            result = json.loads(resp.text).get("data")
        except AttributeError:
            result = resp.json.get("data")

        return result
        
    def main(self):
        domains = self._get_virsh_domains()

        for domain in domains:
            try:
                if not self._query_vmachine(domain):
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
            except RuntimeError as e:
                self.logger.warn(str(e))
                continue