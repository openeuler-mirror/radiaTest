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
import shlex
import tempfile
from subprocess import getoutput, getstatusoutput

from flask import current_app, jsonify

from worker.apps.vmachine.bash import (
    get_bridge_source,
    get_network_source,
)
from worker.utils.bash import rm_vmachine_relate_file


def domain_cli(act, name):
    return getstatusoutput("virsh {} {}".format(shlex.quote(act), shlex.quote(name)))


def domain_state(name):
    return getstatusoutput(
        "export LANG=en_US.UTF-8 && virsh list --all | grep {} | awk -F '{}' ".format(
            shlex.quote(name), shlex.quote(name)
        )
        + " '{print $NF}' | sed 's/^ *//;s/ *$//' "
    )


def attach_device(name, xml):
    tmpfile = tempfile.mkstemp()[1]
    exitcode, output = getstatusoutput(
        "echo -e {} > {} && virsh attach-device {} {} --config".format(
            shlex.quote(xml),
            tmpfile,
            shlex.quote(name),
            tmpfile
        )
    )
    if os.path.exists(tmpfile):
        os.remove(tmpfile)

    return jsonify({"error_code": exitcode, "error_msg": output})


def undefine_domain(name):
    return getstatusoutput(
        "virsh undefine --nvram --remove-all-storage {}".format(shlex.quote(name))
    )


class VmachineBaseSchema:
    def __init__(self, body) -> None:
        self._body = body


class OperateVmachine(VmachineBaseSchema):
    def delete(self):
        names = self._body.get("name")
        if isinstance(names, list):
            for name in names:
                domain_cli("destroy", name)
                rm_vmachine_relate_file('{}.qcow2'.format(name), current_app.config.get("STORAGE_POOL"))
                exitcode, output = undefine_domain(name)
                rm_vmachine_relate_file('{}.log'.format(name), current_app.config.get("LOG_HOME"))
        else:
            domain_cli("destroy", names)
            rm_vmachine_relate_file('{}.qcow2'.format(names), current_app.config.get("STORAGE_POOL"))
            exitcode, output = undefine_domain(names)
            rm_vmachine_relate_file('{}.log'.format(names), current_app.config.get("LOG_HOME"))
        return jsonify({"error_code": exitcode, "error_msg": output})

    def edit(self):
        if self._body.get("memory"):
            exitcode, output = getstatusoutput(
                "virt-xml {} --edit --memory {},maxmemory={}".format(
                    shlex.quote(self._body.get("name")),
                    shlex.quote(str(self._body.get("memory"))),
                    shlex.quote(str(self._body.get("memory"))),
                )
            )

        if self._body.get("sockets") or self._body.get("cores") or self._body.get("threads"):
            vcpus = self._body.get("sockets") * self._body.get("cores") * self._body.get("threads")
            exitcode, output = getstatusoutput(
                "virt-xml {} --edit --vcpus {},sockets={},cores={},threads={}".format(
                    shlex.quote(self._body.get("name")),
                    vcpus,
                    self._body.get("sockets"),
                    self._body.get("cores"),
                    self._body.get("threads"),
                )
            )

        return jsonify({"error_code": exitcode, "error_msg": output})


class OperateVnic(VmachineBaseSchema):
    def add(self):
        if self._body.get("mode") == "bridge":
            source = getoutput(get_bridge_source())
            if not source:
                return jsonify(
                    {
                        "error_code": 1,
                        "error_msg": "The host is not configured with a bridge mode virtual bridge.",
                    }
                )
        else:
            source = getoutput(get_network_source())
            if not source:
                return jsonify(
                    {
                        "error_code": 1,
                        "error_msg": "The host is not configured with a network mode virtual network.",
                    }
                )

        if not self._body.get("mac"):
            self._body["mac"] = getoutput(
                "virt-xml {} --build-xml --network {}={},model={}".format(
                    shlex.quote(self._body.get("name")),
                    shlex.quote(self._body.get("mode")),
                    source,
                    shlex.quote(self._body.get("bus")),
                )
                + " | grep '<mac address=' | awk -F\\\" '{print $2}'"
            )

        exitcode, output = getstatusoutput(
            "virt-xml {} --add-device --network {}={},model={},mac={} --update".format(
                shlex.quote(self._body.get("name")),
                shlex.quote(self._body.get("mode")),
                source,
                shlex.quote(self._body.get("bus")),
                shlex.quote(self._body.get("mac")),
            )
        )
        if exitcode:
            return jsonify({"error_code": exitcode, "error_msg": output})

        self._body.update(
            {
                "mac": self._body.get("mac"),
                "source": source,
            }
        )



        return self._body

    def delete(self):
        exitcode, output = getstatusoutput(
            "virsh detach-interface {} --type {} --mac {} --config --live --persistent".format(
                shlex.quote(self._body.get("name")),
                shlex.quote(self._body.get("mode")),
                shlex.quote(self._body.get("mac")),
            )
        )
        return jsonify({"error_code": exitcode, "error_msg": output})


class OperateVdisk(VmachineBaseSchema):
    def add(self):
        if not self._body.get("volume"):
            sign = int(
                getoutput(
                    "find {} -name '{}*' | wc -l".format(
                        shlex.quote(
                            current_app.config.get("STORAGE_POOL").replace("/$", "")
                        ),
                        shlex.quote(self._body.get("name")),
                    )
                )
            )
            while [True]:
                sign += 1
                self._body.update({"volume": self._body.get("name") + "-" + str(sign)})
                number = getoutput(
                    "find {} -name '{}*' | wc -l".format(
                        shlex.quote(
                            current_app.config.get("STORAGE_POOL").replace("/$", "")
                        ),
                        shlex.quote(self._body.get("volume")),
                    )
                )
                if not int(number):
                    break

        cmd = "virt-xml {} --add-device --disk path={}/{}.qcow2,size={},bus={},cache={} --update".format(
            shlex.quote(self._body.get("name")),
            shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
            shlex.quote(self._body.get("volume")),
            shlex.quote(str(self._body.get("capacity"))),
            shlex.quote(self._body.get("bus")),
            shlex.quote(self._body.get("cache")),
        )
        exitcode, output = getstatusoutput(cmd)

        current_app.logger.info(output)

        if exitcode:
            return jsonify({"error_code": exitcode, "error_msg": output})

        self._body.update({"volume": self._body.get("volume")})

        return self._body

    def delete(self):
        exitcode, output = getstatusoutput(
            "virsh detach-disk {} {}/{}.qcow2 --config --live --persistent".format(
                shlex.quote(self._body.get("name")),
                shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
                shlex.quote(self._body.get("volume")),
            )
        )

        current_app.logger.info(output)

        if exitcode:
            return jsonify({"error_code": exitcode, "error_msg": output})

        exitcode, output = getstatusoutput(
            "rm -rf {}/{}.qcow2".format(
                shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
                shlex.quote(self._body.get("volume")),
            )
        )

        current_app.logger.info(output)

        return jsonify({"error_code": exitcode, "error_msg": output})
