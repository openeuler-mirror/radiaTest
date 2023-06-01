import json
import secrets
import string
from flask import current_app, jsonify
from subprocess import getstatusoutput
from messenger.utils.shell import ShellCmdApi
from messenger.utils.bash import (
    pxe_boot,
    power_on_off,
    pmachine_reset_password,
    get_bmc_user_id,
    reset_bmc_user_passwd,
)
from messenger.utils.pxe import PxeInstall, CheckInstall
from messenger.utils.response_util import RET
from messenger.utils.requests_util import update_request
from messenger.utils.pssh import ConnectionApi


class AutoInstall:
    def __init__(self, body):
        self.pmachine = json.loads(body.get("pmachine"))
        self.mirroring = json.loads(body.get("mirroring"))

    def kickstart(self):
        if not self.mirroring["efi"]:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The milestone image does not provide grub.efi path .",
                }
            )

        if not self.pmachine["mac"]:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The physical machine registration information does not exist in the mac address.",
                }
            )

        if not self.pmachine["ip"]:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The registration information of the physical machine does not have an IP address.",
                }
            )

        result = PxeInstall(
            self.pmachine["mac"],
            self.pmachine["ip"],
            self.mirroring["efi"]
        ).bind_efi_mac_ip()

        if isinstance(result, tuple):
            return result

        exitcode, output = ShellCmdApi(
            pxe_boot(
                self.pmachine["bmc_ip"],
                self.pmachine["bmc_user"],
                self.pmachine["bmc_password"],
            )
        ).exec()

        if exitcode:
            error_msg = (
                    "Failed to boot pxe to start the physical machine:%s."
                    % self.pmachine["ip"]
            )
            current_app.logger.error(error_msg)
            current_app.logger.error(output)

            return jsonify(
                error_code=RET.INSTALL_CONF_ERR,
                error_msg=error_msg
            )

        result = CheckInstall(self.pmachine["ip"]).check()

        if isinstance(result, tuple):
            return result

        return jsonify(
            error_code=RET.OK,
            error_msg="os install succeed"
        )


class OnOff:
    def __init__(self, body) -> None:
        self._body = body
        self.pmachine = body.get("pmachine")

    def on_off(self):
        exitcode, output = ShellCmdApi(
            power_on_off(
                self.pmachine["bmc_ip"],
                self.pmachine["bmc_user"],
                self.pmachine["bmc_password"],
                self._body.get("status"),
            )
        ).exec()

        if exitcode:
            return jsonify(error_code=exitcode, error_msg=output)

        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (self.pmachine["bmc_ip"], self.pmachine["bmc_user"], self.pmachine["bmc_password"])
        )
        if exitcode != 0:
            raise ValueError("The infomation of BMC provided is wrong.")

        return update_request(
            "/api/v1/pmachine/{}".format(
                self.pmachine.get("id")
            ),
            {
                "status": output.split()[-1]
            },
            self._body.get("auth")
        )


class PmachineSshPassword:
    def __init__(self, body) -> None:
        self._body = body

    def reset_password(self):
        random_password = "".join(
            [secrets.choice(string.ascii_letters) for _ in range(3)]
            + [secrets.choice(string.digits) for _ in range(3)]
            + ["\\" + secrets.choice(current_app.config.get("RANDOM_PASSWORD_CHARACTER")) for _ in range(2)]
        )

        new_password = random_password
        ssh = ConnectionApi(
            ip=self._body.get("ip"),
            port=self._body.get("port"),
            user=self._body.get("user"),
            passwd=self._body.get("old_password"),
        )
        conn = ssh.conn()
        if not conn:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Failed to connect to physical machine.",
            )
        exitcode, output = ShellCmdApi(
            pmachine_reset_password(
                self._body.get("user"),
                new_password,
            ), ssh
        ).exec()

        if exitcode:
            return jsonify(
                error_code=RET.BASH_ERROR,
                error_msg="bash execute error:{}".format(output)
            )

        _resp = update_request(
            "/api/v1/pmachine/{}".format(self._body.get("id")),
            {
                "password": new_password.replace("\\", "")
            },
            self._body.get("auth")
        )
        if _resp.get("error_code") != RET.OK:
            return jsonify(
                error_code=_resp.get("error_code"),
                error_msg=_resp.get("error_msg")
            )
        else:
            return jsonify(
                error_code=RET.OK,
                error_msg="pmachine {} change password to {} success".format(self._body.get("ip"), new_password),
                data=[self._body.get("ip"), new_password.replace("\\", "")]
            )


class PmachineBmcPassword:
    def __init__(self, body) -> None:
        self._body = body

    def reset_bmc_password(self):
        exitcode, output = getstatusoutput(
            get_bmc_user_id(
                self._body.get("bmc_ip"),
                self._body.get("bmc_user"),
                self._body.get("old_bmc_password")
            )
        )

        if exitcode != 0:
            return jsonify(
                error_code=RET.BASH_ERROR,
                error_msg="bmc user is not exsists")

        exitcode, output = getstatusoutput(
            reset_bmc_user_passwd(
                self._body.get("bmc_ip"),
                self._body.get("bmc_user"),
                self._body.get("old_bmc_password"),
                output,
                self._body.get("bmc_password"),
            )
        )

        if exitcode != 0:
            return jsonify(
                error_code=RET.BASH_ERROR,
                error_msg="bmc password change failed")

        return jsonify(
            error_code=RET.OK,
            error_msg="bmc password change success"
        )


class PmachineInfo:
    def __init__(self, body) -> None:
        self._body = body

    def check(self):
        bmc_ip = self._body.get("bmc_ip")

        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (bmc_ip, self._body.get("bmc_user"), self._body.get("bmc_password"))
        )
        if exitcode != 0:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg=f"实体机{bmc_ip}的bmc账号或者密码不正确,无法自动释放,请同步最新信息."
            )

        pmachine_status = output.split()[-1]
        if pmachine_status != "on":
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg=f"实体机{bmc_ip}非上电状态,无法验证ssh账号密码,无法自动释放,请保证实体机上电状态."
            )

        conn = ConnectionApi(
            self._body.get("ip"),
            self._body.get("password"),
            self._body.get("port"),
            self._body.get("user"),
        ).conn()
        if not conn:
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg=f"实体机{bmc_ip}的ssh账号或者密码不正确,无法自动释放,请同步最新信息."
            )
        conn.close()

        return jsonify(
            error_code=RET.OK,
            error_msg="pmachine info is correct"
        )
