# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : hukun66
# @email   : hu_kun@hoperun.com
# @Date    : 2023/09/04
# @License : Mulan PSL v2
#####################################
import json
import string
from subprocess import getstatusoutput
from random import choices, sample, choice

from flask import jsonify, request

from messenger.utils.shell import ShellCmdApi
from messenger.utils.bash import (
    power_on_off,
    pmachine_reset_password,
    get_bmc_user_id,
    reset_bmc_user_passwd,
)
from messenger.utils.response_util import RET
from messenger.utils.requests_util import update_request
from messenger.utils.pssh import ConnectionApi


class AutoInstall:
    def __init__(self, body):
        pmachine = body.get("pmachine")
        if isinstance(pmachine, str):
            pmachine = json.loads(pmachine)
        self.pmachine = pmachine

        mirroring = body.get("mirroring")
        if isinstance(mirroring, str):
            mirroring = json.loads(mirroring)
        self.mirroring = mirroring
        self.body = body
        if (not isinstance(self.pmachine, dict)) or (not isinstance(self.mirroring, dict)):
            raise Exception("安装参数必须为json格式")

    def kickstart(self, is_async=False):
        """
        is_async 是否异步执行
        """
        error_msg = None
        if not self.mirroring["efi"]:
            error_msg = "The milestone image does not provide grub.efi path.",
        if not self.mirroring["location"]:
            error_msg = "The milestone image does not provide location path.",
        if not self.mirroring["ks"]:
            error_msg = "The milestone image does not provide ks path.",
        if not self.pmachine["mac"]:
            error_msg = "The physical machine registration information does not exist in the mac address.",
        if not self.pmachine["ip"]:
            error_msg = "The registration information of the physical machine does not have an IP address.",
        if error_msg is not None:
            return jsonify({"error_code": RET.INSTALL_CONF_ERR, "error_msg": error_msg})

        # 是否异步任务提前返回结果
        user = {
            "user_id": self.body.get("user_id"),
            "auth": request.headers.get("authorization"),
        }
        body = {
            "pmachine": self.pmachine,
            "mirroring": self.mirroring,
            "milestone_name": self.body.get("milestone_name"),
            "os_info": self.body.get("os_info"),
            "frame": self.pmachine['frame'],
        }
        # 循环导入规避
        from celeryservice.tasks import run_pxe_install
        if is_async is True:
            run_pxe_install.delay(user, body)
        else:
            run_pxe_install.apply(args=(user, body))

        return jsonify(
            error_code=RET.OK,
            error_msg="succeed"
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
        # 适配密码修改接口
        if self._body.get("password"):
            new_password = self._body.get("password")
        else:
            new_password = ''.join(sample(choices(string.digits, k=4) + 
                                          choices(string.ascii_letters, k=3) + 
                                          [choice(['@', '#'])], k=8))
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
                "password": new_password
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
                data=[self._body.get("ip"), new_password]
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

    def err_response(self, bmc_status='void', power_status='void', ssh_status='void'):
        bmc_ip = self._body.get("bmc_ip")
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg=f"pm state: ip {bmc_ip}, bmc {bmc_status}, power {power_status}, ssh {ssh_status}"
        )

    def check(self):
        bmc_ip = self._body.get("bmc_ip")

        # 1. check bmc user account.
        exitcode, output = getstatusoutput(
            "ipmitool -I lanplus -H %s -U %s  -P %s power status"
            % (bmc_ip, self._body.get("bmc_user"), self._body.get("bmc_password"))
        )
        if exitcode != 0:
            return self.err_response(bmc_status='error')

        # 2. check power status.
        pmachine_status = output.split()[-1]
        if pmachine_status != "on":
            return self.err_response(bmc_status='ok', power_status='off')

        # 3. check os ssh account.
        conn = ConnectionApi(
            self._body.get("ip"),
            self._body.get("password"),
            self._body.get("port"),
            self._body.get("user"),
        ).conn()
        if not conn:
            return self.err_response('ok', 'on', 'error')

        conn.close()

        return jsonify(
            error_code=RET.OK,
            error_msg=f"pm state: ip {bmc_ip}, bmc ok, power on, ssh ok"
        )
