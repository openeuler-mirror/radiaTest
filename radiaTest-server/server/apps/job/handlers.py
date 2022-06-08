import json
from flask import current_app, request, jsonify, g

from server.model.pmachine import Pmachine
from server.model.vmachine import Vmachine
from server.utils.response_util import RET
from server.utils.requests_util import do_request


class JobMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": int(g.gitee_id),
        })
        
        self._body["pmachine_list"] = self.get_machine_list(
            self._body["pmachine_list"],
            Pmachine,
        )
        self._body["vmachine_list"] = self.get_machine_list(
            self._body["vmachine_list"],
            Vmachine,
        )

    def get_machine_list(self, machine_id_list, table):
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

    def send_job(self, machine_group, api):
        _resp = dict()
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
                "authorization": request.headers.get("authorization")
            },
            obj=_resp,
            verify=True if current_app.config.get("CA_VERIFY") == "True" \
            else machine_group.cert_path, 
        )

        if _r !=0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(_resp)