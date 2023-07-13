import json
import datetime
import requests
import pytz

from flask import jsonify

from celeryservice import celeryconfig
from server.utils.response_util import RET
from server import db
from server.model.vmachine import Vmachine
from server.model.pmachine import Pmachine
from celeryservice.lib import TaskHandlerBase
from server.utils.response_util import ssl_cert_verify_error_collect
from server.model.message import Message, MsgType, MsgLevel
from server.utils.db import Insert, Edit
from server.model.permission import Role, ReUserRole
from server.apps.pmachine.handlers import PmachineOccupyReleaseHandler


class LifecycleMonitor(TaskHandlerBase):
    def check_vmachine_lifecycle(self):
        v_machines = Vmachine.query.all()

        for vmachine in v_machines:
            end_time = vmachine.end_time

            if datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")) > \
                    end_time.astimezone(pytz.timezone('Asia/Shanghai')):
                self.logger.info(
                    "vmachine {} is going to be destroyed, with end_time {}".format(
                        vmachine.name, vmachine.end_time
                    )
                )
                db.session.delete(vmachine)

        db.session.commit()

    def check_pmachine_lifecycle(self):
        filter_params = [
            Pmachine.state == "occupied",
            Pmachine.end_time.isnot(None),
            Pmachine.is_release_notification == 0
        ]
        pmachines = Pmachine.query.filter(*filter_params).all()
        pmachine_handler = PmachineOccupyReleaseHandler()
        for pmachine in pmachines:
            end_time = pmachine.end_time
            try:
                if datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai")) > \
                        end_time.astimezone(pytz.timezone('Asia/Shanghai')):
                    self.logger.info(
                        "pmachine {} is going to be released, with end_time {}".format(
                            pmachine.bmc_ip, pmachine.end_time
                        )
                    )

                    body = dict()
                    body.update({
                        "ip": pmachine.ip,
                        "port": pmachine.port,
                        "user": pmachine.user,
                        "password": pmachine.password,
                        "bmc_ip": pmachine.bmc_ip,
                        "bmc_user": pmachine.bmc_user,
                        "bmc_password": pmachine.bmc_password
                    })
                    _resp = CeleryMonitorMessenger(body).send_request(
                        pmachine.machine_group, "/api/v1/pmachine/auto-release-check"
                    )
                    if _resp.get("error_code") != RET.OK:
                        check_res = _resp.get("error_msg")

                        if pmachine.permission_type in ["org", "person"]:
                            role = Role.query.filter_by(name="admin", org_id=pmachine.org_id).first()
                        elif pmachine.permission_type == "group":
                            role = Role.query.filter_by(
                                name="admin", org_id=pmachine.org_id, group_id=pmachine.group_id
                            ).first()
                        else:
                            continue

                        re_role_user = ReUserRole.query.filter_by(role_id=role.id).all()

                        for item in re_role_user:
                            Insert(
                                Message,
                                {
                                    "data": json.dumps(
                                        {
                                            'info': check_res
                                        }
                                    ),
                                    "level": MsgLevel.system.value,
                                    "from_id": 1,
                                    "to_id": item.user_id,
                                    "type": MsgType.text.value,
                                    "org_id": pmachine.org_id
                                }
                            ).single()

                        Insert(
                            Message,
                            {
                                "data": json.dumps(
                                    {
                                        'info': check_res
                                    }
                                ),
                                "level": MsgLevel.system.value,
                                "from_id": 1,
                                "to_id": pmachine.occupier,
                                "type": MsgType.text.value,
                                "org_id": pmachine.org_id
                            }
                        ).single()

                        Edit(Pmachine, {"id": pmachine.id, "is_release_notification": 1}).single(Pmachine, "/pmachine")
                    else:
                        pmachine_handler.release_with_release_scopes(pmachine)
            except Exception as e:
                self.logger.info("pmachine release error:{}".format(e))
                continue

    def main(self):
        self.check_pmachine_lifecycle()
        self.check_vmachine_lifecycle()


class CeleryMonitorMessenger:
    def __init__(self, body):
        self._body = body

    @ssl_cert_verify_error_collect
    def send_request(self, machine_group, api):
        resp = requests.get(
            "https://{}:{}{}".format(
                machine_group.messenger_ip,
                machine_group.messenger_listen,
                api
            ),
            params=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
            },
            verify=celeryconfig.cacert_path
        )
        if resp.status_code != 200:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        try:
            result = json.loads(resp.text)
        except AttributeError:
            result = resp.json()
        return result
