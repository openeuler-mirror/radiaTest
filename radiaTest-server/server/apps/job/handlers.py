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

from flask import current_app, jsonify, g

from server.model.pmachine import Pmachine
from server.model.vmachine import Vmachine
from server.utils.response_util import RET, ssl_cert_verify_error_collect
from server.utils.requests_util import do_request
from server.utils.auth_util import generate_messenger_token
from server.schema.job import PayLoad


class JobMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": g.user_id,
        })

        self._body["pmachine_list"] = self.get_machine_list(
            self._body["pmachine_list"],
            Pmachine,
        )
        self._body["vmachine_list"] = self.get_machine_list(
            self._body["vmachine_list"],
            Vmachine,
        )

    @staticmethod
    def get_machine_list(machine_id_list, table):
        machine_list = []
        for machine_id in machine_id_list:
            machine = table.query.filter_by(id=machine_id).first()
            if machine:
                try:
                    machine_list.append(
                        machine.to_json()
                    )
                except AttributeError:
                    continue
        
        return machine_list

    @ssl_cert_verify_error_collect
    def send_job(self, machine_group, api):
        _resp = dict()
        payload = PayLoad(g.user_id, g.user_login)
        token = generate_messenger_token(payload)
        _r = do_request(
            method="post",
            url="https://{}:{}{}".format(
                machine_group.messenger_ip,
                machine_group.messenger_listen,
                api
            ),
            body=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": f"JWT {token}"
            },
            obj=_resp,
            verify=current_app.config.get("CA_CERT"),
        )

        if _r != 0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(_resp)