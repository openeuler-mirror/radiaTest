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
# @Date    : 2022/10/12
# @License : Mulan PSL v2
#####################################

import smtplib

from email.mime.text import MIMEText
from email.header import Header
from flask import current_app, jsonify

from server.utils.response_util import RET


class Mail:
    def __init__(self, smtp_server=None, smtp_port=None, from_addr=None, password=None):
        self._smtp_server = smtp_server if smtp_server else current_app.config.get("SMTP_SERVER")
        self._smtp_port = smtp_port if smtp_port else current_app.config.get("SMTP_PORT")
        self._from_addr = from_addr if from_addr else current_app.config.get("FROM_ADDR")
        self._password = password if password else current_app.config.get("SMTP_PASSWD")
        self._smtpobj = self._connect_smtp()

    def send_text_mail(self, to_addr, subject=None, text=None):
        _msg = MIMEText(text, "plain", "utf-8")
        _msg["From"] = Header("【radiaTest平台】")
        _msg["To"] = Header("{}".format(to_addr))
        _subject = "{}".format(subject)
        _msg["Subject"] = Header(_subject, "utf-8")
        try:
            self._smtpobj.sendmail(self._from_addr, to_addr, _msg.as_string())
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

    def quit(self):
        self._smtpobj.quit()

    def close(self):
        self._smtpobj.close()

    def _connect_smtp(self):
        try:
            smtpobj = smtplib.SMTP(self._smtp_server, self._smtp_port)
            smtpobj.starttls()
            smtpobj.login(self._from_addr, self._password)
            return smtpobj
        except ConnectionError as e:
            current_app.logger.error(e)
            return None


