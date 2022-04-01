from copy import deepcopy
import json

from flask import current_app, jsonify

from messenger.utils.response_util import RET
from messenger.utils.shell import ShellCmd
from messenger.utils.bash import (
    pxe_boot,
    power_on_off,
)
from messenger.utils.pxe import PxeInstall, CheckInstall
from messenger.utils.response_util import RET
from messenger.utils.requests_util import update_request


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

        exitcode, output = ShellCmd(
            pxe_boot(
                self.pmachine["bmc_ip"],
                self.pmachine["bmc_user"],
                self.pmachine["bmc_password"],
            )
        )._exec()

        if exitcode:
            error_msg = (
                "Failed to boot pxe to start the physical machine:%s."
                % self.pmachine["ip"]
            )
            current_app.logger.error(error_msg)
            current_app.logger.error(output)

            return jsonify(
                error_code=RET.INSTALL_CONF_ERR, 
                error_msg= error_msg
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
        self.pmachine = json.loads(body.get("pmachine"))

    def on_off(self):
        exitcode, output = ShellCmd(
            power_on_off(
                self.pmachine["bmc_ip"],
                self.pmachine["bmc_user"],
                self.pmachine["bmc_password"],
                self._body.get("status"),
            )
        )._exec()

        if exitcode:
            return jsonify(error_code=exitcode, error_msg=output)

        update_body = deepcopy(self.pmachine)
        update_body.pop("id")

        return update_request(
            "/api/v1/pmachine/{}".format(
                self.pmachine.get("id")
            ),
            update_body,
            self._body.get("auth")
        )
