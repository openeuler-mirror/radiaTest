# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/05
# @License : Mulan PSL v2
#####################################

import smtplib

from email.mime.text import MIMEText
from email.header import Header
from flask import current_app, jsonify

from messenger.utils.response_util import RET


class Mail:
    def __init__(
            self,
            pmachine_ip,
            from_addr=None,
            to_addr=None,
            text="from radiaTest email"
    ):
        self._smtp_server = current_app.config.get("SMTP_SERVER")
        self._smtp_port = current_app.config.get("SMTP_PORT")
        self._from_addr = from_addr if from_addr else current_app.config.get("FROM_ADDR")
        self._to_addr = to_addr if to_addr else current_app.config.get("TO_ADDR")
        self._password = current_app.config.get("SMTP_PASSWD")
        self._pmachine_ip = pmachine_ip
        self._text = text

    def send_text_mail(self):
        _msg = MIMEText(self._text, "plain", "utf-8")
        _msg["From"] = Header("【radiaTest平台】")
        _msg["To"] = Header("radiaTest管理员")
        _subject = "【radiaTest平台】{}-密码变更通知".format(self._pmachine_ip)
        _msg["Subject"] = Header(_subject, "utf-8")
        smtpobj = self._connect_smtp()
        try:
            smtpobj.sendmail(self._from_addr, self._to_addr, _msg.as_string())
            return jsonify(
                error_code=RET.OK,
                error_msg="send mail success"
            )
        except smtplib.SMTPException as e:
            current_app.logger.error(e)
            return jsonify(
                error_code=RET.MAIL_ERROR,
                error_msg="fail to send mail"
            )
        finally:
            smtpobj.close()

    def _connect_smtp(self):
        smtpobj = smtplib.SMTP()
        try:
            smtpobj.connect(self._smtp_server, self._smtp_port)
            smtpobj.login(self._from_addr, self._password)
        except ConnectionError as e:
            current_app.logger.error(e)
        return smtpobj
