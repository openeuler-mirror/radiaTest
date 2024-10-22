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
import json
import time
import shlex
import xml.dom.minidom
from typing import Dict, List
from subprocess import getstatusoutput
from xml.dom.minidom import Element

import libvirt
from libvirt import virDomain, libvirtError
import requests

from celeryservice import celeryconfig
from celeryservice.lib import TaskHandlerBase, AuthTaskHandler
from worker.utils.bash import rm_vmachine_relate_file


class IllegalMonitor(TaskHandlerBase):
    def _get_virsh_domains(self):
        names = []
        try:
            conn = libvirt.openReadOnly(None)
            domains: List[virDomain] = conn.listAllDomains()
            return list(map(lambda d: d.name(), domains))
        except libvirtError as le:
            self.logger.error(f"list domain names error@_get_virsh_domains {le}")
            return names

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
            raise RuntimeError("the worker cannot connect to server@IllegalMonitor")

        result = resp.json().get("data")

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
        domains = self.list_domains_status()
        if not domains:
            return
        try:
            _ = self._update_vmachine(domains)
        except RuntimeError as e:
            self.logger.error(f'update status error@VmachinesStatusMonitor {e}')

    @staticmethod
    def parse_domain_xml(d: str) -> Dict:
        dom_info = dict()
        dom_tree = xml.dom.minidom.parseString(d)
        collection = dom_tree.documentElement
        devices = collection.getElementsByTagName("devices")

        if not devices:
            return dom_info
        dev_ele: Element = devices[0]
        g: Element = dev_ele.getElementsByTagName('graphics')[0]
        g_type = g.getAttribute('type')
        vnc_port = g.getAttribute('port')
        vnc_listen = g.getAttribute('listen')

        if g_type != 'vnc':
            return dom_info

        dom_info['vnc_port'] = int(vnc_port)
        dom_info['vnc_token'] = vnc_listen.replace('.', '-') + '-' + str(vnc_port)
        return dom_info

    def list_domains_status(self) -> Dict:
        domain_status = dict()
        try:
            conn = libvirt.openReadOnly(None)
            domains: List[virDomain] = conn.listAllDomains()
        except libvirtError as le:
            self.logger.error(f"list_domains_status connect or list error {le}")
            return domain_status

        for d in domains:
            name = d.name()
            status_str = 'paused'
            update_info = {}
            try:
                status, _ = d.state()
            except libvirtError as le:
                domain_status[name] = {'status': status_str}
                self.logger.error(f"list_domains_status get domain info error {name} {le}")
                continue

            vnc_port = None
            vnc_token = None
            if status == 1:
                dom_xml = d.XMLDesc()
                dom_info = self.parse_domain_xml(dom_xml)
                vnc_port = dom_info.get('vnc_port')
                vnc_token = dom_info.get('vnc_token')
                status_str = 'running'
            elif status == 5:
                status_str = 'shut off'

            update_info['status'] = status_str
            if vnc_port is not None:
                update_info['vnc_port'] = vnc_port

            if vnc_token is not None:
                update_info['vnc_token'] = vnc_token

            domain_status[name] = update_info
        return domain_status

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
            result = resp.json().get("error_msg")
        except AttributeError:
            result = str(resp.content)

        self.logger.info("update vm status result:{}".format(result))
        return result
