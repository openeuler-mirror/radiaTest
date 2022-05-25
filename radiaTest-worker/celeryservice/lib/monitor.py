import json
import shlex
import requests
from subprocess import getoutput, getstatusoutput
import time
from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase, AuthTaskHandler

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



class VmStatusMonitor(AuthTaskHandler):
    def __init__(self, logger, auth, body):
        self._body = body
        self._user = body.get("user_id", "unknown")
        super().__init__(logger, auth)

    def main(self, promise):
        try:
            self.logger.info(
                "user {0} attempt to create vmachine by cd_rom from {1}".format(
                    self._user,
                    self._body.get("url"),
                )
            )
            
            self.next_period()
            promise.update_state(
                state="_STARTING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )
            for _ in range(celeryconfig.wait_vm_install):
                exitcode = getstatusoutput(
                    "export LANG=en_US.utf-8 ; test \"$(eval echo $(virsh list --all | grep '{}' | awk -F '{} *' ".format(
                    shlex.quote(self._body.get("name")), shlex.quote(self._body.get("name"))
                    )
                    + "'{print $NF}'))\" == 'shut off'"
                    )[0]
                if exitcode == 0:
                    time.sleep(celeryconfig.wait_vm_shutdown)
                    exitcode, output = getstatusoutput(
                        "virsh start {}".format(shlex.quote(self._body.get("name")))
                    )
                    break
                time.sleep(1)

            exitcode, output = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
                + " | awk -F '  ' '{print $NF}')"
            )

            self.next_period()
            promise.update_state(
                state="_SUCCESS",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

        except (RuntimeError, TypeError, KeyError, AttributeError):
            promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )