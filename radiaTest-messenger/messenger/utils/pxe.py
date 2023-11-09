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
import threading
import time
from contextlib import contextmanager
from datetime import datetime

import pytz
from flask import current_app, jsonify
from paramiko import SSHException

from messenger.utils.response_util import RET
from messenger.utils.shell import ShellCmd, ShellCmdApi
from messenger.utils.pssh import ConnectionApi
from messenger.utils.bash import (
    check_ip,
    judge_bind,
    backup_conf,
    clear_bind_mac,
    bind_mac,
    restart_dhcp,
    restore_dhcp,
    inquire_ip,
    pxe_boot,
    rsync_http_dir_to_local,
    annotating_dhcp_conf
)


class DHCP:
    def __init__(self) -> None:
        self._conn = None
        if not self.base_exec_cmd(check_ip(current_app.config.get("PXE_IP"))):
            self._conn = ConnectionApi(
                current_app.config.get("PXE_IP"),
                port=current_app.config.get("PXE_SSH_PORT"),
                user=current_app.config.get("PXE_SSH_USER"),
                pkey=current_app.config.get("PRIVATE_KEY"),
            )
            self._conn.conn()

    def base_exec_cmd(self, cmd):
        return ShellCmd(cmd, self._conn)._bexec()

    def exec_cmd(self, cmd):
        return ShellCmd(cmd, self._conn)._exec()


class PxeInstall(DHCP):
    # 适配单例模式
    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not getattr(cls, "_instance"):
            with cls._instance_lock:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, pmachine, mirroring) -> None:
        super().__init__()
        self.pmachine = pmachine
        self.mirroring = mirroring
        self._mac = pmachine["mac"]
        self._ip = pmachine["ip"]
        self._efi = mirroring["efi"]
        self.tftp_root = current_app.config.get("PXE_TFTP_ROOT")
        self.httpd_root = current_app.config.get("PXE_HTTPD_ROOT")
        self.httpd_prefix = current_app.config.get("PXE_HTTPD_PREFIX")

        self.dhcp_lock_time = None

    @contextmanager
    def get_dhcp_lock(self):
        # dhcp锁最多锁定5分钟
        while True:
            if not self.dhcp_lock_time:
                break
            else:
                now = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
                if (now - self.dhcp_lock_time).seconds > 5 * 60:
                    break
            current_app.logger.info("sleep 10s,wait dhcp lock release!")
            time.sleep(10)
        self.dhcp_lock_time = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        yield
        if self.dhcp_lock_time:
            self.dhcp_lock_time = None

    def clear_bind(self):
        if self.base_exec_cmd(judge_bind(self._mac)):
            exitcode, output = self.exec_cmd(backup_conf())
            if exitcode:
                current_app.logger.error(output)
                self._conn.close()

                return False

            exitcode, output = self.exec_cmd(clear_bind_mac(self._mac))
            if exitcode:
                current_app.logger.error(output)
                exitcode, output = self.exec_cmd(restore_dhcp())
                if exitcode:
                    current_app.logger.error(output)
                current_app.logger.debug("dhcp configuration item cleanup failed.")
                self._conn.close()
                return False
        # 注释手动绑定过的mac地址
        self.exec_cmd(annotating_dhcp_conf(self._mac))
        return True

    def bind_efi_mac_ip(self, tftp_efi):
        # 对修改dhcp文件操作进行上锁，避免同时操作引发异常
        with self.get_dhcp_lock():
            if self.clear_bind() is False:
                return False
            exitcode, output = self.exec_cmd(bind_mac(tftp_efi, self._mac, self._ip))
            if exitcode:
                current_app.logger.error(output)
                exitcode, output = self.exec_cmd(restore_dhcp())
                if exitcode:
                    current_app.logger.error(output)
                    self._conn.close()
                current_app.logger.debug(f"{self._ip} Failed to bind mac address.")
                return False

            exitcode, output = self.exec_cmd(restart_dhcp())
            if exitcode:
                current_app.logger.error(output)

                exitcode1, output1 = self.exec_cmd(restore_dhcp())
                exitcode2, output2 = self.exec_cmd(restart_dhcp())
                if exitcode1 or exitcode2:
                    current_app.logger.error(output1)
                    current_app.logger.error(output2)
                self._conn.close()
                current_app.logger.debug(f"{self._ip} Failed to bind mac address.")
                return False
            return True

    def close_conn(self):
        if self._conn:
            self._conn._client.close()

    def get_boot_file_by_name(self, path, name):
        find_cmd = f"cd {path} && find {name}|tail -n 1"
        exitcode, output = self.exec_cmd(find_cmd)
        if exitcode:
            return False, ''
        return True, output

    def check_efi_file(self, efi_file):
        exitcode, output = self.exec_cmd(f"ls {self.tftp_root}/{efi_file}")
        if exitcode:
            return False
        return True

    def sync_boot_file(self, os_name, template_ks, template_grub):
        if not self._efi.startswith("http"):
            # 支持手动适配过的pxe
            current_app.logger.info(f"使用已适配的efi引导文件：{self._efi}")
            return True, self._efi
        # http地址需要同步至pxe服务器
        relative_path = f"radia_test/{self._ip}"
        sync_efi_path = f"{self.tftp_root}/{relative_path}"
        pxe_boot_file_path = f"{sync_efi_path}/pxeboot"
        efi_name = self._efi.split("/")[-1]
        self.exec_cmd(f"rm -rf {sync_efi_path} && mkdir -p {pxe_boot_file_path}")
        # sync efi file
        exitcode, output = self.exec_cmd(rsync_http_dir_to_local(
            self._efi, sync_efi_path, cut_num=self._efi.count("/") - 3))
        if exitcode:
            current_app.logger.error(f"efi引导文件同步失败")
            return False, output

        pxeboot_url = self.mirroring["location"] + "/images/pxeboot/"
        exitcode1, output1 = self.exec_cmd(rsync_http_dir_to_local(
            pxeboot_url, pxe_boot_file_path, cut_num=pxeboot_url.count("/") - 2))
        if exitcode1:
            current_app.logger.error(f"pxeboot目录同步失败")
            return False, output
        # config ks
        sftp = self._conn._client.open_sftp()
        relative_ks_path = f"ks/radia_test/{self._ip}.ks"
        target_ks = f"{self.httpd_root}/{relative_ks_path}"
        self.exec_cmd(f"mkdir -p {self.httpd_root}/ks/radia_test && rm -rf {target_ks}")
        sftp.put(template_ks, target_ks)
        modify_ks = 'sed -i "s#{os_repo}#%s#" %s' % (self.mirroring["location"], target_ks)
        target_grub = f"{sync_efi_path}/grub.cfg"
        exitcode2, output2 = self.exec_cmd(modify_ks)
        if exitcode2:
            current_app.logger.error(f"{target_ks}修改失败")
            return False, output2
        # config grub.cfg
        sftp.put(template_grub, target_grub)
        sftp.close()
        flag1, linux_file = self.get_boot_file_by_name(pxe_boot_file_path, "vmlinu*")
        flag2, initrd_file = self.get_boot_file_by_name(pxe_boot_file_path, "initr*")
        if not all([flag1, flag2]):
            return False, "pxe引导文件同步失败"
        # 固定的cfg模版替换关键参数，方便后期动态调整安装启动参数
        modify_cfg = """
target_grub=%s
relative_path=%s
sed -i "s#{replace_os_name}#%s#" ${target_grub}
sed -i "s#{replace_ks}#%s#" ${target_grub}
sed -i "s#{replace_linux}#${relative_path}/%s#" ${target_grub}
sed -i "s#{replace_initrd}#${relative_path}/%s#" ${target_grub}
""" % (target_grub, f'{relative_path}/pxeboot', os_name,
            f"{self.httpd_prefix}/{relative_ks_path}", linux_file, initrd_file)
        exitcode2, output2 = self.exec_cmd(modify_cfg)
        if exitcode2:
            current_app.logger.error(f"{target_grub}修改失败")
            return False, output2
        return True, f"{relative_path}/{efi_name}"

    def set_pxe_boot(self):
        exitcode, output = ShellCmdApi(
            pxe_boot(
                self.pmachine["bmc_ip"],
                self.pmachine["bmc_user"],
                self.pmachine["bmc_password"],
            )
        ).exec()
        if exitcode:
            return False
        else:
            return True


class CheckInstall:
    def __init__(self, ip) -> None:
        self._ip = ip

    def check(self, root_pwd):
        client = ConnectionApi(self._ip, root_pwd)

        for _ in range(1800):
            conn = client.conn()
            if conn:
                break
            time.sleep(1)
        else:
            return False

        if not conn:
            return False
        return True


class QueryIp(DHCP):
    def __init__(self, mac) -> None:
        super().__init__()

        self._mac = mac

    def query(self):
        ip = None

        try:
            if not self._mac:
                raise RuntimeError(
                    "worker callback error: have not receive mac from worker"
                )

            for _ in range(30):
                ip = ShellCmd(inquire_ip(self._mac), self._conn)._exec()[1]
                if ip is not None:
                    break
                time.sleep(1)
        
        except (SSHException, RuntimeError) as e:
            current_app.logger.error(str(e))

        if isinstance(ip, str):
            return ip.strip()
        else:
            return jsonify(
                error_code=RET.NET_CONECT_ERR, 
                error_msg="未获取到ip."
            )
