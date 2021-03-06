from shlex import quote

from flask.globals import current_app

# DHCP & PXE

# 检查ip
def check_ip(ip):
    return "ip a | grep {}".format(quote(ip))

# PXE
# 检查mac地址是否已经绑定
def judge_bind(mac):
    return "grep -zoe '\";.    hardware ethernet {};.    fixed-address' {}".format(
        quote(mac), current_app.config.get("DHCP_CONF")
    )

# dhcp配置文件备份
def backup_conf():
    return "/usr/bin/cp -f {} {}.bak".format(
        current_app.config.get("DHCP_CONF"),
        current_app.config.get("DHCP_CONF"),
    )

# 清理原本已绑定的mac
def clear_bind_mac(mac):
    return "sed -zi ':label; s#host {}".format(
        quote(mac.replace(":", "_"))
    ) + "{.*;\\n *}\{1\}##g' %s" % (current_app.config.get("DHCP_CONF"),)

# 绑定mac地址
def bind_mac(efi, mac, ip):
    filename = '    filename "{}";\n'.format(quote(efi)) if efi else None
    return (
        "echo -e 'host {}".format(quote(mac.replace(":", "_")))
        + "{\n"
        + filename
        + "    hardware ethernet {};\n    fixed-address {}".format(
            quote(mac), quote(ip)
        )
        + ";\n}' >> "
        + current_app.config.get("DHCP_CONF")
    )

# 重启dhcp
def restart_dhcp():
    return "systemctl restart dhcpd"

# 回滚dhcp
def restore_dhcp():
    return "/usr/bin/cp -f %s.bak %s" % (
        current_app.config.get("DHCP_CONF"),
        current_app.config.get("DHCP_CONF"),
    )

# pxe引导启动物理机
def pxe_boot(ip, user, password):
    ipmitool_cmd = "ipmitool -I lanplus -H {} -U {}  -P {}".format(
        quote(ip), quote(user), quote(password)
    )
    return "%s chassis bootdev pxe && %s power reset" % (ipmitool_cmd, ipmitool_cmd)

# 物理机 上下电
def power_on_off(ip, user, password, status):
    return "ipmitool -I lanplus -H {} -U {}  -P {} power {}".format(
        quote(ip), quote(user), quote(password), quote(status)
    )


# pmachine释放后修改密码
def pmachine_reset_password(user, new_password):
    return "echo '{}:{}'| chpasswd" .format(quote(user), quote(new_password))


# 查询物理机Administrator用户id
def get_bmc_user_id(bmc_user):
    return ("ipmitool user list 1 | grep -i {}" .format(quote(bmc_user))
    + " |awk '{print $1}' | shuf -n 1")


# 修改物理机Administrator用户bmc密码
def reset_bmc_user_passwd(bmc_id, bmc_password):
    return "ipmitool user set password {} {}".format(
        quote(bmc_id), quote(bmc_password)
    )

# 查询ip地址
def inquire_ip(mac):
    return (
        "tac /var/lib/dhcpd/dhcpd.leases | tr [A-F] [a-f] | sed -n '/{}".format(
            quote(mac)
        )
        + "/,/lease/p' | awk '{if ($1 == \"lease\") print $2}' | tr -d ';' | head -n 1 | sed -e 'e#/#-#g'"
    )

class ResourceQueryCli:
    # 查询内存用量
    mem_usage_cli = "echo $(free | grep -w Mem | awk '{print $3}') $(free | grep -w Mem | awk '{print $2}') | awk '{print $1/$2*100}'"

    # 查询内存总量
    mem_total_cli = "echo $(free | grep -w Mem | awk '{print $2/(1024*1024)}')"

    # 查询CPU型号
    cpu_index_cli = "export LANG=en_US.UTF-8 && lscpu | grep -i '^model name:' | awk -F ': *' '{print $NF}'"

    # 查询CPU用量
    cpu_usage_cli = "LAST_CPU_IDLE=$(cat /proc/stat | grep -w cpu | awk '{print $5}') && LAST_CPU_TOTAL=$(cat /proc/stat | grep -w cpu | awk '{print $2+$3+$4+$5+$6+$7+$8}') && sleep 1 && NEXT_CPU_IDLE=$(cat /proc/stat | grep -w cpu | awk '{print $5}') && NEXT_CPU_TOTAL=$(cat /proc/stat | grep -w cpu | awk '{print $2+$3+$4+$5+$6+$7+$8}') && CPU_IDLE=$(echo $NEXT_CPU_IDLE $LAST_CPU_IDLE | awk '{print $1 - $2}') && CPU_TOTAL=$(echo $NEXT_CPU_TOTAL $LAST_CPU_TOTAL | awk '{print $1 - $2}') && CPU_USAGE=$(echo $CPU_IDLE $CPU_TOTAL | awk '{print 100-$1/$2*100}') && echo $CPU_USAGE"

    #  查询cpu数量
    cpu_num_cli = "cat /proc/cpuinfo | grep 'physical id' | sort | uniq | wc -l"

    cpu_physical_cores_cli = "cat /proc/cpuinfo | grep 'cpu cores' | uniq | awk '{print $4}'"

    cpu_logical_cores_cli = "cat /proc/cpuinfo | grep 'processor' | wc -l"

    #  查询os信息
    os_cli = "cat /etc/os-release | grep -w PRETTY_NAME | awk -F '\"' '{print $2}'"

    #  查询kernel信息
    kernel_cli = "echo $(uname -s) $(uname -r)"


# rsync相关命令

# 生成临时密码文件，必须在push pull之前生成
def rsync_password_file_generator():
    return "echo {} > {} && chmod 600 {}".format(
        current_app.config.get("RSYNC_PASSWORD"),
        current_app.config.get("RSYNC_PASSWORD_FILE"),
        current_app.config.get("RSYNC_PASSWORD_FILE"),
    )

# rsync客户端向rsync服务端推送文件
def rsync_dir_push(path, job_name):
    return "rsync -artvzP --password-file={} {} {}@{}::{}/{}".format(
        current_app.config.get("RSYNC_PASSWORD_FILE"),
        quote(path),
        current_app.config.get("RSYNC_USER"),
        current_app.config.get("REPO_IP"),
        current_app.config.get("RSYNC_MODULE"),
        quote(job_name),
    )

# 删除临时密码文件
def rsync_password_file_delete():
    return "rm -rf {}".format(current_app.config.get("RSYNC_PASSWORD_FILE"))
