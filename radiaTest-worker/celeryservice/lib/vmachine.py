# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/05
# @License : Mulan PSL v2
#####################################

import os
import time
import shlex
import json
from subprocess import getoutput, getstatusoutput
from urllib.parse import urlparse
import requests

from celeryservice import celeryconfig
from celeryservice.lib import AuthTaskHandler
from worker.utils.bash import (
    get_network_source,
    install_base,
    rm_disk_image,
    domain_cli,
    undefine_domain,
)


class VmachineBaseSchema(AuthTaskHandler):
    def __init__(self, logger, auth, body):
        self._body = body
        self._user = body["user_id"] if body.get("user_id") else "unknown"
        self._vmachine = body["name"] if body.get("name") else "unknown"
        super().__init__(logger, auth)

    def delete_vmachine(self, body):
        domain_cli("destroy", body.get("name"))
        exitcode, output = undefine_domain(body.get("name"))
        self.logger.info(output)
        if exitcode:
            self.logger.error("Fail to delete vmachine {0}.").format(
                body.get("id"),
            )

    def update_vmachine(self, body):
        _ = requests.put(
            url="https://{}:{}/api/v1/vmachine/callback".format(
                celeryconfig.messenger_ip,
                celeryconfig.messenger_listen,
            ),
            data=json.dumps(body),
            headers={
                "authorization": self.auth,
                **celeryconfig.headers,
            },
            verify=celeryconfig.cacert_path,
        )

    def update_task_status(self, body):
        url = "https://{}/api/v1/vmachine/{}/data".format(
            celeryconfig.server_addr,
            body.get("id"), )
        self.logger.info(url)

        _ = requests.put(
            url=url,
            data=json.dumps({
                "status": "failure",
            }),
            headers={
                "authorization": self.auth,
                **celeryconfig.headers,
            },
            verify=True if celeryconfig.ca_verify == "True" else celeryconfig.cacert_path
        )


class InstallVmachine(VmachineBaseSchema):
    def kickstart(self, promise):
        self.logger.info(
            "user {0} attempt to create vmachine by autoinstall from {1}".format(
                self._user,
                self._body["location"]
            )
        )

        promise.update_state(
            state="CREATING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,

            },
        )
        try:
            source = getoutput(get_network_source())
            if not source:
                output = "network mode virtual bridge is not configured"
                self.logger.error(
                    "user {0} fail to create vmachine by autoinstall from {1}, because {2}".format(
                        self._user,
                        self._body["location"],
                        output
                    )
                )
                raise RuntimeError(output)

            exitcode, output = getstatusoutput(
                "qemu-img create -f qcow2 {}/{}.qcow2 {}G".format(
                    shlex.quote(celeryconfig.storage_pool.replace("/$", "")),
                    shlex.quote(self._body.get("name")),
                    shlex.quote(str(self._body.get("capacity"))),
                )
            )
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine by autoinstall from {1}, because {2}".format(
                        self._user,
                        self._body["location"],
                        output
                    )
                )
                raise RuntimeError(output)

            self.next_period()
            promise.update_state(
                state="INSTALLING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,

                },
            )

            cmd = " {} --network network={} --location {} --extra-args ks={}".format(
                install_base(self._body, celeryconfig.storage_pool),
                source,
                shlex.quote(self._body.get("location")),
                shlex.quote(self._body.get("ks")),
            )
            exitcode, output = getstatusoutput(cmd)
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine by autoinstall from {1}, because {2}".format(
                        self._user,
                        self._body["location"],
                        output
                    )
                )
                raise RuntimeError(output)

            self.next_period()
            promise.update_state(
                state="STARTING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,

                },
            )

            for _ in range(int(celeryconfig.autoinstall_expired_time)):
                exitcode = getstatusoutput(
                    "export LANG=en_US.utf-8 ; test \"$(eval echo $(virsh list --all | \
                     grep '{}' | awk -F '{} *' ".format(
                        shlex.quote(self._body.get("name")), shlex.quote(self._body.get("name"))
                    )
                    + "'{print $NF}'))\" == 'shut off'"
                )[0]
                if exitcode == 0:
                    _, _ = getstatusoutput(
                        "virsh start {}".format(shlex.quote(self._body.get("name")))
                    )
                    break
                time.sleep(3)

            _, _ = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
                + " | awk -F '  ' '{print $NF}')"
            )

            self.next_period()
            promise.update_state(
                state="SUCCESS",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

            self.logger.info(
                "user {0} finish to create vmachine by autoinstall from {1}".format(
                    self._user,
                    self._body["location"],
                )
            )

            self._body.update(
                {
                    "mac": getoutput(
                        "virsh dumpxml %s | grep -Pzo  \"<interface type='bridge'>[\s\S] *<mac address.*\" |grep -Pzo '<mac address.*' | awk -F\\' '{print $2}' | head -1"
                        % self._body.get("name")
                    ).strip(),
                    "status": "running",
                    "vnc_port": domain_cli("vncdisplay", self._body.get("name"))[1]
                        .strip("\n")
                        .split(":")[-1],
                }
            )

            self._set_static_vncport()

            self.update_vmachine(self._body)

        except (RuntimeError, TypeError, KeyError, AttributeError):
            rm_disk_image(
                self._body.get("name"),
                celeryconfig.storage_pool,
            )
            self.update_task_status(self._body)

            exitcode, output = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
            )
            self.logger.info(exitcode)
            if exitcode == 0:
                self.delete_vmachine(self._body)

            promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

    def import_type(self, promise):
        self.logger.info(
            "user {0} attempt to create vmachine imported from {1}".format(
                self._user,
                self._body["url"],
            )
        )

        self.next_period()
        promise.update_state(
            state="DOWNLOADING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            },
        )

        self._body.update(
            {"source": celeryconfig.network_interface_source}
        )
        block_file = str()
        sha256_filename = "/tmp/" + self._body.get("name") + ".sha256sum"
        try:
            if celeryconfig.disk_cache_on == "True":
                url_analyse_resp = urlparse(self._body.get("url"))
                source_qcow2_file = os.path.join(celeryconfig.local_source_storage_pool, url_analyse_resp.path[1:])
                source_path = os.path.dirname(source_qcow2_file)
                qcow2_name = os.path.basename(source_qcow2_file)
                block_file = os.path.join(source_path, "block.txt")
                source_qcow2_sha256 = source_qcow2_file + ".sha256sum"
                if not os.path.exists(source_qcow2_file):
                    os.makedirs(os.path.dirname(source_qcow2_file))
                    self._download_qcow2(block_file, source_qcow2_file)
                else:
                    while True:
                        if os.path.exists(block_file):
                            self.logger.info("waiting for local source download...")
                            time.sleep(30)
                        else:
                            break
                    if os.path.exists(source_qcow2_sha256):
                        _, local_sha256 = getstatusoutput(
                            "head -1 %s | awk '{print $1}'" % source_qcow2_sha256
                        )
                    else:
                        _, local_sha256 = getstatusoutput(
                            "sha256sum %s | awk '{print $1}'" % source_qcow2_file
                        )
                    exitcode, output = getstatusoutput(
                        "wget -nv -c {} -O {} 2>&1".format(
                            self._body.get("url") + ".sha256sum",
                            sha256_filename
                        )
                    )
                    if exitcode:
                        self.logger.error(
                            "{} did not  have sha256sum file,can't make sure local qcow2 is latest".format(qcow2_name)
                        )
                        raise RuntimeError(output)
                    _, remote_sha256 = getstatusoutput(
                        "head -1 %s | awk '{print $1}'" % sha256_filename
                    )
                    if local_sha256 != remote_sha256:
                        self._download_qcow2(block_file, source_qcow2_file)
                exitcode, output = getstatusoutput(
                    "cp {} {}/{}.qcow2 2>&1".format(
                        source_qcow2_file,
                        shlex.quote(celeryconfig.storage_pool),
                        shlex.quote(self._body.get("name")),
                    )
                )
            else:
                exitcode, output = getstatusoutput(
                    "sudo wget -nv -c {} -O {}/{}.qcow2 2>&1".format(
                        shlex.quote(self._body.get("url")),
                        shlex.quote(celeryconfig.storage_pool),
                        shlex.quote(self._body.get("name")),
                    )
                )
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine imported from {1}, because {2}".format(
                        self._user,
                        self._body["url"],
                        output,
                    )
                )
                raise RuntimeError(output)

            self.next_period()
            promise.update_state(
                state="IMPORTING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

            exitcode, output = getstatusoutput(
                "{} --import --noreboot".format(install_base(self._body, celeryconfig.storage_pool))
            )
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine imported from {1}, because {2}".format(
                        self._user,
                        self._body["url"],
                        output,
                    )
                )

                raise RuntimeError(output)

            self.next_period()
            promise.update_state(
                state="STARTING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

            exitcode, output = domain_cli("start", self._body.get("name"))
            if exitcode:
                exitcode, result = undefine_domain(self._body.get("name"))
                if not exitcode:
                    self.logger.error(
                        "user {0} fail to create vmachine imported from {1}, because {2}".format(
                            self._user,
                            self._body["url"],
                            output + "&" + result,
                        )
                    )
                    raise RuntimeError(output + "&" + result)
                self.logger.error(
                    "user {0} fail to create vmachine imported from {1}, because {2}".format(
                        self._user,
                        self._body["url"],
                        output,
                    )
                )
                raise RuntimeError(output)

            self._body.update(
                {
                    "mac": getoutput(
                        "virsh dumpxml %s | grep -Pzo  \"<interface type='bridge'>[\s\S] *<mac address.*\" |grep -Pzo '<mac address.*' | awk -F\\' '{print $2}' | head -1"
                        % self._body.get("name")
                    ).strip(),
                    "status": "running",
                    "vnc_port": domain_cli(
                        "vncdisplay", self._body.get("name"))[1]
                        .strip("\n")
                        .split(":")[-1],
                }
            )

            self._set_static_vncport()

            self.update_vmachine(self._body)

            self.logger.info(
                "user {0} finish to create vmachine imported from {1}".format(
                    self._user,
                    self._body["url"],
                )
            )

            self.next_period()
            promise.update_state(
                state="SUCCESS",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,

                },
            )
        except (RuntimeError, TypeError, KeyError, AttributeError):
            self.logger.info(self._body)
            rm_disk_image(
                self._body.get("name"),
                celeryconfig.storage_pool,
            )

            self.update_task_status(self._body)

            exitcode, output = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
            )
            self.logger.info(exitcode)
            if exitcode == 0:
                self.delete_vmachine(self._body)

            promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )
        finally:
            if os.path.exists(block_file):
                os.remove(block_file)
            if os.path.exists(sha256_filename):
                os.remove(sha256_filename)

    def cd_rom(self, promise):
        self.logger.info(
            "user {0} attempt to create vmachine by cd_rom from {1}".format(
                self._user,
                self._body.get("url"),
            )
        )

        self.next_period()
        promise.update_state(
            state="CREATING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            },
        )

        self._body.update(
            {"source": celeryconfig.network_interface_source}
        )
        try:
            exitcode, output = getstatusoutput(
                "qemu-img create -f qcow2 {}/{}.qcow2 {}G".format(
                    shlex.quote(celeryconfig.storage_pool.replace("/$", "")),
                    shlex.quote(self._body.get("name")),
                    shlex.quote(str(self._body.get("capacity"))),
                )
            )
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine by cd_rom from {1}, because {2}".format(
                        self._user,
                        self._body.get("url"),
                        output,
                    )
                )
                raise RuntimeError(output)

            self.next_period()
            promise.update_state(
                state="CDROMMING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )
            cmd = " {} --cdrom {} -d --noreboot".format(
                install_base(self._body, celeryconfig.storage_pool),
                shlex.quote(self._body.get("url")),
            )

            exitcode, output = getstatusoutput(cmd)
            if exitcode:
                self.logger.error(
                    "user {0} fail to create vmachine cdromming by cd_rom from {1}, because {2}".format(
                        self._user,
                        self._body["url"],
                        output,
                    )
                )
                raise RuntimeError(output)

            exitcode, output = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
                + " | awk -F '  ' '{print $NF}')"
            )
            self._body.update(
                {
                    "mac": getoutput(
                        "virsh dumpxml %s | grep -Pzo  \"<interface type='bridge'>[\s\S] *<mac address.*\" |grep -Pzo '<mac address.*' | awk -F\\' '{print $2}' | head -1"
                        % self._body.get("name")
                    ).strip(),
                    "status": output,
                    "vnc_port": domain_cli("vncdisplay", self._body.get("name"))[1]
                        .strip("\n")
                        .split(":")[-1],
                }
            )

            self._set_static_vncport()

            self.update_vmachine(self._body)

            self.next_period()
            promise.update_state(
                state="INSTALLING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,

                },
            )

            self.next_period()
            promise.update_state(
                state="SUCCESS",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

            self.logger.info(
                "user {0} finish to create vmachine by cd-rom with {1}.qcow2 from {2}".format(
                    self._user,
                    self._body.get("name"),
                    self._body.get("url"),
                )
            )

        except (RuntimeError, TypeError, KeyError, AttributeError):
            self.logger.info(self._body)
            rm_disk_image(
                self._body.get("name"),
                celeryconfig.storage_pool,
            )
            self.update_task_status(self._body)

            exitcode, output = getstatusoutput(
                "export LANG=en_US.utf-8 ; eval echo $(virsh list --all | grep '{}' ".format(
                    shlex.quote(self._body.get("name"))
                )
            )
            self.logger.info(exitcode)
            if exitcode == 0:
                self.delete_vmachine(self._body)

            promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

    def _download_qcow2(self, block_file, source_qcow2_file):
        exitcode, output = getstatusoutput(
            "echo block > {};sudo wget -nv -c {} -O {} 2>&1".format(
                block_file,
                self._body.get("url"),
                source_qcow2_file
            )
        )
        if exitcode:
            self.logger.error(
                "user {0} fail to store vmachine in local from {1}, because {2}".format(
                    self._user,
                    self._body["url"],
                    output,
                )
            )
            raise RuntimeError(output)
        _, _ = getstatusoutput(
            "wget -nv -c {} -O {} 2>&1".format(
                self._body.get("url") + ".sha256sum",
                source_qcow2_file + ".sha256sum"
            )
        )

    def _set_static_vncport(self):
        cmd = "sh {} {} {} {}".format(
            shlex.quote(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "worker/utils/virsh_config.sh"
                )
            ),
            shlex.quote(self._body.get("name")),
            shlex.quote("vncport"),
            int(self._body.get("vnc_port")) + celeryconfig.vnc_start_port
        )
        exitcode, output = getstatusoutput(cmd)
        if exitcode:
            self.logger.error("vmachine vncport failed to edit:{}".format(output))
