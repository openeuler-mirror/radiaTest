# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-17 16:50:37
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


import time

from flask import current_app, jsonify
from flask.helpers import send_file


from server.utils.shell import ShellCmd
from server.utils.pssh import Connection
from server.utils.bash import (
    check_ip,
    judge_bind,
    backup_conf,
    clear_bind_mac,
    bind_mac,
    restart_dhcp,
    restore_dhcp,
    inquire_ip,
)


class DHCP:
    def __init__(self) -> None:
        if ShellCmd(check_ip(current_app.config.get("PXE_IP")))._bexec():
            self._conn = None
        else:
            self._conn = Connection(
                current_app.config.get("PXE_IP"),
                port=current_app.config.get("PXE_SSH_PORT"),
                user=current_app.config.get("PXE_SSH_USER"),
                pkey=current_app.config.get("PRIVATE_KEY"),
            )
            self._conn._conn()


class PxeInstall(DHCP):
    def __init__(self, mac, ip, efi) -> None:
        super().__init__()

        self._mac = mac
        self._ip = ip
        self._efi = efi.strip()

    def clear_bind(self):
        if ShellCmd(judge_bind(self._mac), self._conn)._bexec():
            exitcode, output = ShellCmd(backup_conf(), self._conn)._exec()
            if exitcode:
                current_app.logger.error(output)
                self._conn._close()
                return jsonify(
                    {
                        {
                            "error_code": 50008,
                            "error_mesg": "dhcp configuration file backup failed, please contact the administrator to deal with it in time.",
                        }
                    }
                )

            exitcode, output = ShellCmd(clear_bind_mac(self._mac), self._conn)._exec()
            if exitcode:
                current_app.logger.error(output)
                exitcode, output = ShellCmd(restore_dhcp(), self._conn)._exec()
                if exitcode:
                    current_app.logger.error(output)
                    self._conn._close()
                    return jsonify(
                        {
                            {
                                "error_code": 50008,
                                "error_mesg": "dhcp configuration item cleanup failed and recovery failed, please contact the administrator in time.",
                            }
                        }
                    )

                self._conn._close()
                return jsonify(
                    {
                        "error_code": 50008,
                        "error_mesg": "dhcp configuration item cleanup failed.",
                    }
                )

    def bind_efi_mac_ip(self):
        output = self.clear_bind()
        if isinstance(output, tuple):
            return output

        exitcode, output = ShellCmd(
            bind_mac(self._efi, self._mac, self._ip), self._conn
        )._exec()
        if exitcode:
            current_app.logger.error(output)
            exitcode, output = ShellCmd(restore_dhcp(), self._conn)._exec()
            if exitcode:
                current_app.logger.error(output)
                self._conn._close()
                return jsonify(
                    {
                        {
                            "error_code": 50008,
                            "error_mesg": "Failed to bind the mac address and recovery failed, please contact the administrator in time.",
                        }
                    }
                )

            self._conn._close()
            return jsonify(
                {{"error_code": 50008, "error_mesg": "Failed to bind mac address."}}
            )

        exitcode, output = ShellCmd(restart_dhcp(), self._conn)._exec()
        if exitcode:
            current_app.logger.error(output)

            exitcode1, output1 = ShellCmd(restore_dhcp(), self._conn)._exec()
            exitcode2, output2 = ShellCmd(restart_dhcp(), self._conn)._exec()
            if exitcode1 or exitcode2:
                current_app.logger.error(output1)
                current_app.logger.error(output2)
                self._conn._close()
                return jsonify(
                    {
                        {
                            "error_code": 50008,
                            "error_mesg": "Failed to bind the mac address and recovery failed, please contact the administrator in time.",
                        }
                    }
                )

            self._conn._close()
            return jsonify(
                {
                    {
                        "error_code": 50008,
                        "error_mesg": "Failed to bind mac address.",
                    }
                }
            )

    def close_conn(self):
        self._conn._client.close()


class CheckInstall:
    def __init__(self, ip) -> None:
        self._ip = ip

    def check(self):
        # TODO pxe安装后的密码，后续需要处理（lemon.higgins）
        client = Connection(self._ip, "openEuler12#$")  

        for _ in range(1800):
            conn = client._conn()
            if conn:
                break
            time.sleep(1)

        if not conn:
            return jsonify(
                {
                    "error_code": 50010,
                    "error_mesg": "Cannot connect to the installed machine, you need to check whether the installation is successful, or whether the provided user name and password are correct.",
                }
            )


class QueryIp(DHCP):
    def __init__(self, mac) -> None:
        super().__init__()

        self._mac = mac

    def query(self):
        for _ in range(30):
            ip = ShellCmd(inquire_ip(self._mac), self._conn)._exec()[1]
            if ip:
                break
            time.sleep(1)

        if ip:
            return ip.strip()
        else:
            return jsonify({"error_code": 30011, "error_mesg": "未获取到ip."})
