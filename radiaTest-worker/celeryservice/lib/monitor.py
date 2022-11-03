import re
import json
import shlex
from subprocess import getstatusoutput
import requests
import time

from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase, AuthTaskHandler
from worker.utils.bash import rm_vmachine_relate_file


class IllegalMonitor(TaskHandlerBase):
    def _get_virsh_domains(self):
        exitcode, output = getstatusoutput(
            "virsh list --all | sed -n '$d; 1,2!p' | awk '{print $2}'"
        )
        if exitcode == 0:
            return output.splitlines()

        return []

    def _query_vmachine(self, domain):
        resp = requests.get(
            "https://{}/api/v1/vmachine/check-exist".format(
                celeryconfig.server_addr,
            ),
            params={
                "domain": domain,
            },
            headers=celeryconfig.headers,
            verify=True if celeryconfig.ca_verify == "True" else \
                celeryconfig.cacert_path
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

                    exitcode, output = getstatusoutput(
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

                    rm_vmachine_relate_file(
                        "{}.qcow2".format(shlex.quote(domain)),
                        celeryconfig.storage_pool,
                    )
                    self.logger.info(
                        f"the qcow2 of the illegal vmachine {domain} has been deleted."
                    )

                    exitcode, output = getstatusoutput(
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
                        f"the domain of illegal vmachine {domain} has been deleted."
                    )
                    rm_vmachine_relate_file(
                        "{}.log".format(shlex.quote(domain)),
                        celeryconfig.log_home,
                    )

                    self.logger.info(
                        f"the log of the illegal vmachine {domain} has been deleted."
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


class VmachinesStatusMonitor(TaskHandlerBase):
    @staticmethod
    def _get_virsh_info():
        exitcode, output = getstatusoutput(
            "export LANG=en_US.utf-8 ;virsh list --all | sed -n '$d; 1,2!p'"
        )

        if exitcode == 0:
            return output.split("\n")

        return []

    def main(self):
        vmachines = self._get_virsh_info()
        values_num = len(vmachines)

        domains_run = list()
        domains_shut_off = list()
        if values_num == 0:
            self.logger.info("no vm in worker, nothing need update status")
            return
        elif values_num >= 10:
            count = 0
            for _ in range(values_num):
                vmachine = vmachines.pop()
                count += 1
                if count % 10 == 0:
                    try:
                        _ = self._update_vmachine(domains_run, domains_shut_off)
                    except RuntimeError as e:
                        self.logger.error(str(e))
                    finally:
                        count = 0
                        domains_run.clear()
                        domains_shut_off.clear()
                        continue
                else:
                    domain = re.findall(r'\w+-\w+-\w+-\w+.\w+-\w+', vmachine)
                    if "running" in vmachine:
                        domains_run.extend(domain)
                    else:
                        domains_shut_off.extend(domain)
        else:
            for vmachine in vmachines:
                domain = re.findall(r'\w+-\w+-\w+-\w+.\w+-\w+', vmachine)
                if "running" in vmachine:
                    domains_run.extend(domain)
                else:
                    domains_shut_off.extend(domain)

        if len(domains_run) == 0 and len(domains_shut_off) == 0:
            pass
        else:
            try:
                _ = self._update_vmachine(domains_run, domains_shut_off)
            except RuntimeError as e:
                self.logger.error(str(e))

    def _update_vmachine(self, domains_run, domains_shut_off):
        resp = requests.put(
            "https://{}/api/v1/vmachine/update-status".format(
                celeryconfig.server_addr,
            ),
            data=json.dumps(
                {
                    "domains_run": {
                        "domain": domains_run,
                        "status": "running"
                    },
                    "domains_shut_off": {
                        "domain": domains_shut_off,
                        "status": "shut off"
                    }
                }
            ),
            headers=celeryconfig.headers,
            verify=True if celeryconfig.ca_verify == "True" else \
                celeryconfig.cacert_path
        )
        if resp.status_code != 200:
            raise RuntimeError("the worker cannot connect to server")

        try:
            result = json.loads(resp.text).get("error_msg")
        except AttributeError:
            result = resp.json.get("error_msg")

        self.logger.info("update result:{}".format(result))
        return result
