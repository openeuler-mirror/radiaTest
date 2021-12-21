# -*- coding: utf-8 -*-
# @Author : lemon-higgins
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Date   : 2021-11-05 14:44:05


from shlex import quote

from flask.globals import current_app

# 检查ip
def check_ip(ip):
    return "ip a | grep {}".format(quote(ip))


# PXE
## 检查mac地址是否已经绑定
def judge_bind(mac):
    return "grep -zoe '\";.    hardware ethernet {};.    fixed-address' {}".format(
        quote(mac), quote(current_app.config.get("DHCP_CONF"))
    )


## dhcp配置文件备份
def backup_conf():
    return "/usr/bin/cp -f {} {}.bak".format(
        quote(current_app.config.get("DHCP_CONF")),
        quote(current_app.config.get("DHCP_CONF")),
    )


## 清理原本已绑定的mac
def clear_bind_mac(mac):
    return "sed -zi ':label; s#host {}".format(
        quote(mac.replace(":", "_"))
    ) + "{.*;\\n *}\{1\}##g' %s" % (current_app.config.get("DHCP_CONF"),)


## 绑定mac地址
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


## 重启dhcp
def restart_dhcp():
    return "systemctl restart dhcpd"


## 回滚dhcp
def restore_dhcp():
    return "/usr/bin/cp -f %s.bak %s" % (
        current_app.config.get("DHCP_CONF"),
        current_app.config.get("DHCP_CONF"),
    )


## pxe引导启动物理机
def pxe_boot(ip, user, password):
    ipmitool_cmd = "ipmitool -I lanplus -H {} -U {}  -P {}".format(
        quote(ip), quote(user), quote(password)
    )
    return "%s chassis bootdev pxe && %s power reset" % (ipmitool_cmd, ipmitool_cmd)


## 物理机 上下电
def power_on_off(ip, user, password, status):
    return "ipmitool -I lanplus -H {} -U {}  -P {} power {}".format(
        quote(ip), quote(user), quote(password), quote(status)
    )


## 查询ip地址
def inquire_ip(mac):
    return (
        "tac /var/lib/dhcpd/dhcpd.leases | tr [A-F] [a-f] | sed -n '/{}".format(
            quote(mac)
        )
        + "/,/lease/p' | awk '{if ($1 == \"lease\") print $2}' | tr -d ';' | head -n 1 | sed -e 'e#/#-#g'"
    )


## 部署mugen框架
def deploy_mugen_framwork(machine):
    return "cd {}/mugen && \
                bash mugen.sh -c --ip {} --password {} --port {} --user {}".format(
        current_app.config.get("TEST_MACHINE_FRAMEWORK_PATH"),
        quote(machine.ip),
        quote(machine.password),
        quote(str(machine.port)),
        quote(machine.user),
    )


# rsync相关命令

## 生成临时密码文件，必须在push pull之前生成
def rsync_password_file_generator():
    return "echo {} > {} && chmod 600 {}".format(
        current_app.config.get("RSYNC_PASSWORD"),
        current_app.config.get("RSYNC_PASSWORD_FILE"),
        current_app.config.get("RSYNC_PASSWORD_FILE"),
    )

## rsync客户端向rsync服务端推送文件
def rsync_dir_push(path, job_name):
    return "rsync -artvzP --password-file={} {} {}@{}::{}/{}".format(
        current_app.config.get("RSYNC_PASSWORD_FILE"),
        path,
        current_app.config.get("RSYNC_USER"),
        current_app.config.get("REPO_IP"),
        current_app.config.get("RSYNC_MODULE"),
        job_name,
    )

## 删除临时密码文件
def rsync_password_file_delete():
    return "rm -rf {}".format(current_app.config.get("RSYNC_PASSWORD_FILE"))
