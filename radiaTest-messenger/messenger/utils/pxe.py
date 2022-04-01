import time

from flask import current_app, jsonify
from flask.helpers import send_file
from paramiko import SSHException
from .response_util import RET


from messenger.utils.shell import ShellCmd
from messenger.utils.pssh import Connection
from messenger.utils.bash import (
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
                            "error_code": RET.NET_CONF_ERR,
                            "error_msg": "dhcp configuration file backup failed, please contact the administrator to deal with it in time.",
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
                                "error_code": RET.NET_CONF_ERR,
                                "error_msg": "dhcp configuration item cleanup failed and recovery failed, please contact the administrator in time.",
                            }
                        }
                    )

                self._conn._close()
                return jsonify(
                    {
                        "error_code": RET.NET_CONF_ERR,
                        "error_msg": "dhcp configuration item cleanup failed.",
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
                            "error_code": RET.NET_CONF_ERR,
                            "error_msg": "Failed to bind the mac address and recovery failed, please contact the administrator in time.",
                        }
                    }
                )

            self._conn._close()
            return jsonify(
                {{"error_code": RET.NET_CONF_ERR, "error_msg": "Failed to bind mac address."}}
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
                            "error_code": RET.NET_CONF_ERR,
                            "error_msg": "Failed to bind the mac address and recovery failed, please contact the administrator in time.",
                        }
                    }
                )

            self._conn._close()
            return jsonify(
                {
                    {
                        "error_code": RET.NET_CONF_ERR,
                        "error_msg": "Failed to bind mac address.",
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
                    "error_code": RET.NET_CONECT_ERR,
                    "error_msg": "Cannot connect to the installed machine, you need to check whether the installation is successful, or whether the provided user name and password are correct.",
                }
            )


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
