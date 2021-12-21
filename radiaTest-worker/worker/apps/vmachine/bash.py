from shlex import quote
from subprocess import getoutput

from flask import current_app


def install_base(body):
    fixed_mac = ""
    if body.get("mac"):
        fixed_mac = ",mac={}".format(quote(body.get("mac")))

    controller = ""
    if body.get("frame") == "aarch64":
        controller = "--controller type=pci,model=pcie-root-port,index=50"

    cmd = (
        "virt-install --os-type generic --name {} --memory {} --vcpus {},sockets={},cores={},threads={} --cpu={}  --disk path={}/{}.qcow2,bus={} ".format(
            quote(body.get("name")),
            quote(str(body.get("memory"))),
            quote(
                str(
                    int(body.get("sockets"))
                    * int(body.get("cores"))
                    * int(body.get("threads"))
                )
            ),
            quote(str(body.get("sockets"))),
            quote(str(body.get("cores"))),
            quote(str(body.get("threads"))),
            quote(body.get("cpu_mode")),
            quote(current_app.config.get("STORAGE_POOL").replace("/$", "")),
            quote(body.get("name")),
            quote(body.get("disk_bus")),
        )
        + " --network {}={},model={}".format(
            quote(body.get("net_mode")),
            getoutput(" virsh iface-list | sed '1,2d' | awk '{print $1}' | head -1"),
            quote(body.get("net_bus")),
        )
        + fixed_mac
        + " --video={} --noautoconsole --graphics vnc,listen={} --check path_in_use=1 --os-variant unknown {} ".format(
            quote(body.get("video_bus")),
            quote(body.get("host")),
            controller,
        )
    )
    return cmd


def get_bridge_source():
    return "virsh iface-list | sed '1,2d;/^$/d'  | grep -v '^ lo' | awk '{print $1}' | shuf -n1"


def get_network_source():
    return "virsh net-list | sed '1,2d;/^$/d' | awk '{print $1}' | shuf -n 1"
