import os
from shlex import quote
from subprocess import getoutput, getstatusoutput


def install_base(body, storage_pool):
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
            quote(storage_pool.replace("/$", "")),
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


def rm_vmachine_relate_file(name, path):
    return getoutput(
        "rm -rf {}".format(
            os.path.join(quote(path), quote(name))
        )
    )


def domain_cli(act, name):
    return getstatusoutput("virsh {} {}".format(quote(act), quote(name)))


def domain_state(name):
    return getstatusoutput(
        "export LANG=en_US.UTF-8 && virsh list --all | grep {} | awk -F '{}' ".format(
            quote(name), quote(name)
        )
        + " '{print $NF}' | sed 's/^ *//;s/ *$//' "
    )


def undefine_domain(name):
    return getstatusoutput(
        "virsh undefine --nvram --remove-all-storage {}".format(quote(name))
    )
