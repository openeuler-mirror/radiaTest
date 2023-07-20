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

from datetime import datetime
from pathlib import Path

import pytz
from flask import current_app

from celeryservice.lib.job.handler import RunJob
from messenger.utils.pxe import PxeInstall, CheckInstall
from messenger.utils.requests_util import create_request


class PXEAutoInstall(RunJob):
    def get_template_ks(self):
        os_name = self._body["os_info"]["name"]
        os_version = self._body["os_info"]["version"]
        template_ks = Path(__file__).parent.joinpath(f"{os_name}-{os_version}-ks.template")
        if not template_ks.exists():
            template_ks = Path(__file__).parent.joinpath(f"{os_name}-ks.template")
            if not template_ks.exists():
                template_ks = Path(__file__).parent.joinpath(f"common-ks.template")

        current_app.logger.info(f"ks模版使用{template_ks.absolute()}")
        return template_ks

    def run(self):
        os_name = self._body.get("milestone_name") + "_" + self._body["frame"]
        pmachine_ip = self._body['pmachine'].get('ip')
        template_grub = Path(__file__).parent.joinpath("grub_template.cfg")
        template_ks = self.get_template_ks()
        try:
            self._body["name"] = f"物理机{self._body['pmachine'].get('ip')}安装{os_name}" \
                                 + " " + self.start_time.strftime("%Y-%m-%d %H:%M:%S")
            self._create_job(multiple=False, is_suite_job=False)
            self._update_job(
                status="SYNC BOOT FILES",
            )
            pxe_install = PxeInstall(self._body["pmachine"], self._body["mirroring"])
            flag, res = pxe_install.sync_boot_file(os_name, template_ks.absolute(), template_grub.absolute())
            if flag is True and pxe_install.check_efi_file(res) is True:
                self._update_job(
                    status="BIND EFI MAC IP",
                )
                if pxe_install.bind_efi_mac_ip(res) is not True:
                    self._update_job(
                        result="fail",
                        remark="bind efi mac ip failed!",
                        end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                        status="BLOCK",
                    )
                else:
                    self._update_job(
                        status="SET PXE BOOT",
                    )
                    if pxe_install.set_pxe_boot() is False:
                        self._update_job(
                            result="fail",
                            remark="set pxe boot failed!",
                            end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                            status="BLOCK",
                        )
                    else:
                        self._update_job(
                            status="INSTALLING",
                        )
                        # 检查安装是否完成
                        if CheckInstall(self._body["pmachine"]["ip"]).check() is True:
                            self._update_job(
                                result="success",
                                status="FINISHED",
                            )
                            data = dict(info=f"系统提示您：<b>{pmachine_ip}</b>物理机安装{os_name}<b>成功</b>。")
                            create_request(
                                "/api/v1/msg/text_msg",
                                {
                                    "data": data,
                                    "to_ids": [self.user.get("user_id")]
                                },
                                self.user.get("auth")
                            )
                            return True
                        else:
                            self._update_job(
                                result="fail",
                                remark="install timeout!",
                                end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                                status="BLOCK",
                            )

            else:
                current_app.logger.error(f"{self._body['pmachine']['ip'] } install failed, error msg: {res}")
                self._update_job(
                    result="fail",
                    remark="sync boot files failed!",
                    end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                    status="BLOCK",
                )

        except RuntimeError as e:
            self.logger.error(str(e))
            self._update_job(
                result="fail",
                remark=str(e),
                end_time=datetime.now(tz=pytz.timezone('Asia/Shanghai')),
                status="BLOCK",
            )

        data = dict(info=f"系统提醒您：<b>{pmachine_ip}</b>物理机安装{os_name}<b>失败</b>!")
        create_request(
            "/api/v1/msg/text_msg",
            {
                "data": data,
                "to_ids": [self.user.get("user_id")]
            },
            self.user.get("auth")
        )
        return False
