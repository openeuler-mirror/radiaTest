# -*- coding: utf-8 -*-
# @Author : lemon-higgins
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Date   : 2021-11-02 17:16:43


import time
import shlex
import tempfile
from subprocess import getoutput, getstatusoutput

from flask import current_app, jsonify

from worker.apps.vmachine.bash import (
    get_bridge_source,
    get_network_source,
    install_base,
)


def rm_disk_image(name):
    return getoutput(
        "rm -rf {}/{}.qcow2".format(
            shlex.quote(current_app.config.get("STORAGE_POOL")),
            shlex.quote(name),
        )
    )


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
    tmpfile = tempfile.mkstemp()
    exitcode,output = getstatusoutput(
        "echo -e {} > {} && virsh attach-device {} {} --config".format(
            shlex.quote(xml),
            tmpfile[1],
            shlex.quote(name),
            tmpfile[1]
        )
    )
    
    return jsonify({"error_code": exitcode, "error_mesg": output})
    


def undefine_domain(name):
    return getstatusoutput(
        "virsh undefine --nvram --remove-all-storage {}".format(shlex.quote(name))
    )


class VmachineBase:
    def __init__(self, body) -> None:
        self._body = body


class InstallVmachine(VmachineBase):
    def kickstart(self):
        source = getoutput(get_network_source())
        if not source:
            return jsonify(
                {
                    "error_code": 1,
                    "error_code": "The host is not configured with a network mode virtual bridge.",
                }
            )

        exitcode, output = getstatusoutput(
            "qemu-img create -f qcow2 {}/{}.qcow2 {}G".format(
                shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
                shlex.quote(self._body.get("name")),
                shlex.quote(str(self._body.get("capacity"))),
            )
        )
        if exitcode:
            return jsonify({"error_code": exitcode, "status": output})

        cmd = " {} --network network={} --location {} --extra-args ks={}".format(
            install_base(self._body),
            source,
            shlex.quote(self._body.get("location")),
            shlex.quote(self._body.get("ks")),
        )
        exitcode, output = getstatusoutput(cmd)

        if exitcode:
            return jsonify({"error_code": exitcode, "status": output})

        for _ in range(900):
            exitcode = getstatusoutput(
                "export LANG=en_US.utf-8 ; test \"$(eval echo $(virsh list --all | grep '{}' | awk -F '{} *' ".format(
                shlex.quote(self._body.get("name")), shlex.quote(self._body.get("name"))
                )
                + "'{print $NF}'))\" == 'shut off'"
                )[0]
            if exitcode == 0:
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
        return jsonify(self._body)

    def _import(self):
        self._body.update(
            {"source": current_app.config.get("NETWORK_INTERFACE_SOURCE")}
        )

        exitcode, output = getstatusoutput(
            "sudo wget -nv -c {} -O {}/{}.qcow2 2>&1".format(
                shlex.quote(self._body.get("url")),
                shlex.quote(current_app.config.get("STORAGE_POOL")),
                shlex.quote(self._body.get("name")),
            )
        )
        if exitcode:
            current_app.logger.error(output)
            rm_disk_image(self._body.get("name"))
            return jsonify({"error_code": exitcode, "error_mesg": output})

        exitcode, output = getstatusoutput(
            "{} --import --noreboot".format(install_base(self._body))
        )
        if exitcode:
            rm_disk_image(self._body.get("name"))
            return jsonify({"error_code": 31000, "error_mesg": output})

        exitcode, output = domain_cli("start", self._body.get("name"))
        if exitcode:
            exitcode, result = undefine_domain(self._body.get("name"))
            if not exitcode:
                return jsonify(
                    {"error_code": 31002, "error_mesg": output + " & " + result}
                )
            return jsonify({"error_code": 31001, "error_mesg": output})

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

        return jsonify(self._body)

    def cd_rom(self):
        exitcode, output = getstatusoutput(
            "qemu-img create -f qcow2 {}/{}.qcow2 {}G".format(
                shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
                shlex.quote(self._body.get("name")),
                shlex.quote(str(self._body.get("capacity"))),
            )
        )
        if exitcode:
            return jsonify({"error_code": exitcode, "status": output})

        exitcode, output = getstatusoutput(
            "{} --cdrom {} --noreboot".format(install_base(self._body), self._body.get("url"))
        )
        if exitcode:
            rm_disk_image(self._body.get("name"))
            return jsonify({"error_code": 31000, "error_mesg": output})
        
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

        return jsonify(self._body)


class OperateVmachine(VmachineBase):
    def delete(self):
        domain_cli("destroy", self._body.get("name"))
        exitcode, output = undefine_domain(self._body.get("name"))
        return jsonify({"error_code": exitcode, "error_mesg": output})

    def edit(self):
        pass


class OperateVnic(VmachineBase):
    def add(self):
        if self._body.get("mode") == "bridge":
            source = getoutput(get_bridge_source())
            if not source:
                return jsonify(
                    {
                        "error_code": 1,
                        "error_code": "The host is not configured with a bridge mode virtual bridge.",
                    }
                )
        else:
            source = getoutput(get_network_source())
            if not source:
                return jsonify(
                    {
                        "error_code": 1,
                        "error_code": "The host is not configured with a network mode virtual network.",
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
            return jsonify({"error_code": exitcode, "error_mesg": output})

        self._body.update(
            {
                "mac": self._body.get("mac"),
                "source": source,
            }
        )

        if exitcode:
            return jsonify({"error_code": exitcode, "error_mesg": output})

        return self._body

    def delete(self):
        exitcode, output = getstatusoutput(
            "virsh detach-interface {} --type {} --mac {} --config --live --persistent".format(
                shlex.quote(self._body.get("name")),
                shlex.quote(self._body.get("mode")),
                shlex.quote(self._body.get("mac")),
            )
        )
        return jsonify({"error_code": exitcode, "error_mesg": output})


class OperateVdisk(VmachineBase):
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
        if exitcode:
            return jsonify({"error_code": exitcode, "error_mesg": output})

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
        if exitcode:
            return jsonify({"error_code": exitcode, "error_mesg": output})

        exitcode, output = getstatusoutput(
            "rm -rf {}/{}.qcow2".format(
                shlex.quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
                shlex.quote(self._body.get("volume")),
            )
        )

        return jsonify({"error_code": exitcode, "error_mesg": output})
