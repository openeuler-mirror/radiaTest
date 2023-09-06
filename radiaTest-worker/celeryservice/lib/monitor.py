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

import re
import json
import shlex
from subprocess import getstatusoutput
from copy import deepcopy
import requests
import time

from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase, AuthTaskHandler
from worker.apps.vmachine.handlers import domain_cli
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
    def main(self):
        """
        批量请求更新虚拟机数据(单次小于等于10)
        """
        vmachines_info = self._get_virsh_info()
        values_num = len(vmachines_info)

        domains = dict()
        if values_num == 0:
            self.logger.info("no vm in worker, nothing need update status")
            return
        elif values_num >= 10:
            count = 0
            for _ in range(values_num):
                if count != 0 and count % 10 == 0:
                    try:
                        _ = self._update_vmachine(domains)
                    except RuntimeError as e:
                        self.logger.error(str(e))
                    finally:
                        count = 0
                        domains.clear()
                        continue
                else:
                    vmachine_name, vmachine_info = vmachines_info.popitem()
                    count += 1
                    domains.update({
                        vmachine_name: vmachine_info
                    })
        else:
            for vmachine_name, vmachine_info in vmachines_info.items():
                domains.update({
                    vmachine_name: vmachine_info
                })

        if not domains:
            pass
        else:
            try:
                _ = self._update_vmachine(domains)
            except RuntimeError as e:
                self.logger.error(str(e))

    def _get_virsh_info(self):
        """
        获取虚拟机的状态,vncport
        :return : Type[dict]
        """
        exitcode, output = getstatusoutput(
            "export LANG=en_US.utf-8 ;virsh list --all | sed -n '$d; 1,2!p'"
        )
        vmachines_info = dict()
        _body = dict()
        vmachines = output.split("\n")
        if exitcode == 0 and len(vmachines) != 0:
            for vmachine in vmachines:
                _body.clear()
                vmachine_name = re.findall(r'\w+-\w+-\w+-\w+.\w+-\w+', vmachine)[0]
                if "running" in vmachine:
                    vnc_port = int(domain_cli("vncdisplay", vmachine_name)[1].strip("\n").split(":")[-1])
                    vnc_token = celeryconfig.worker_ip.replace(".", "-") + "-" \
                                + str(vnc_port + celeryconfig.vnc_start_port)
                    _body.update({
                        'vnc_port': vnc_port,
                        'status': "running",
                        'vnc_token': vnc_token
                    })
                elif "shut off" in vmachine:
                    _body.update({
                        'status': "shut off"
                    })
                else:
                    _body.update({
                        'status': "paused"
                    })
                body = deepcopy(_body)
                vmachines_info.update({
                    vmachine_name: body
                })

            self.logger.info("we will sync vmachine info:{}".format(vmachines_info))
            return vmachines_info

        return {}

    def _update_vmachine(self, domains):
        resp = requests.put(
            "https://{}/api/v1/vmachine/update-status".format(
                celeryconfig.server_addr,
            ),
            data=json.dumps(domains),
            headers=celeryconfig.headers,
            verify=True if celeryconfig.ca_verify == "True" else \
                celeryconfig.cacert_path
        )
        if resp.status_code != 200:
            raise RuntimeError("the worker request to server error happened:{}".format(resp.status_code))

        try:
            result = json.loads(resp.text).get("error_msg")
        except AttributeError:
            result = resp.json.get("error_msg")

        self.logger.info("update result:{}".format(result))
        return result
