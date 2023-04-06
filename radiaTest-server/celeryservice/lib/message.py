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

import datetime
import pytz

from flask import json
from sqlalchemy.exc import SQLAlchemyError

from celeryservice import celeryconfig
from server.model.vmachine import Vmachine
from server.model.user import User
from server.utils.mail_util import Mail
from celeryservice.lib import TaskHandlerBase
from server.model.message import Message, MsgType, MsgLevel
from server.utils.db import Insert


class VmachineReleaseNotice(TaskHandlerBase):
    def send_vmachine_release_message(self):
        max_endtime = datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")) + \
                      datetime.timedelta(days=1)
        filter_params = [
            Vmachine.is_release_notification == 0,
            Vmachine.end_time < max_endtime,
        ]
        v_machines = Vmachine.query.filter(*filter_params).all()
        user_vmachines = dict()

        if v_machines:
            mail = Mail(
                smtp_server=celeryconfig.smtp_server,
                smtp_port=int(celeryconfig.smtp_port),
                from_addr=celeryconfig.from_addr,
                password=celeryconfig.smtp_passwd
            )
            try:
                for vmachine in v_machines:
                    if vmachine.ip:
                        user_vmachines.setdefault(
                            '%s_%s' % (str(vmachine.creator_id), str(vmachine.org_id)), []
                        ).append(vmachine.name)
                self.logger.info("we will send message to user,it's detail:{}".format(user_vmachines))

                for key, value in user_vmachines.items():
                    vmachines = ','.join(value)
                    user_org = key.split('_')

                    Insert(
                        Message,
                        {
                            "data": json.dumps(
                                {
                                    'info': f'您在平台创建的部分虚拟机即将过期，如需继续使用，请尽快延期:'
                                            f'<b>{vmachines}</b>'
                                }
                            ),
                            "level": MsgLevel.system.value,
                            "from_id": 1,
                            "to_id": user_org[0],
                            "type": MsgType.text.value,
                            "org_id": user_org[1]
                        }
                    ).insert_id()

                    re_vmachine = Vmachine.query.filter(Vmachine.name.in_(value)).all()
                    for single_vmachine in re_vmachine:
                        single_vmachine.is_release_notification = 1
                        single_vmachine.add_update()

                    text = "Some virtual machines you created on the radiaTest platform will be " \
                           "released one day later," \
                           "If you still want to use it, log in to the platform, then delay them:{}".format(vmachines)
                    userinfo = User.query.filter_by(user_id=user_org[0]).first()
                    if userinfo.cla_email:
                        mail.send_text_mail(userinfo.cla_email, subject="【radiaTest平台】虚拟机释放通知", text=text)
            except (ConnectionError, SQLAlchemyError) as e:
                self.logger.error(e)
            finally:
                mail.close()
        else:
            pass

    def main(self):
        self.send_vmachine_release_message()
