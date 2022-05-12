import abc
from copy import deepcopy
import json
import time
from random import choice
from httplib2 import Response

import requests
from flask import current_app, jsonify, request

from messenger.utils import DateEncoder
from messenger.utils.pssh import Connection
from messenger.utils.pxe import QueryIp
from messenger.utils.token_creator import VncTokenCreator
from messenger.utils.response_util import RET
from messenger.utils.requests_util import create_request, do_request, query_request, update_request


class MessageBody:
    def __init__(self, body) -> None:
        self._body = body


class AuthMessageBody(MessageBody):
    def __init__(self, auth, body) -> None:
        self.auth = auth
        super().__init__(body)


class ChoosePmachine(AuthMessageBody):
    def __init__(self, auth, body, algorithm) -> None:
        super().__init__(auth, body)

        self._pmachines = query_request(
            "/api/v1/accessable_machines",
            {
                "machine_group_id": body.get("machine_group_id"),
                "machine_purpose": "create_vmachine",
                "machine_type": "physical",
                "frame": body.get("frame")
            },
            self.auth
        )
        if not self._pmachines:
            self._pmachines = []

        self._algorithm = algorithm

    def run(self):
        org_len = len(self._pmachines)
        while len(self._pmachines) > 0:
            pm = self._algorithm(self._pmachines)
            result = check_available_mem(
                pm.get("ip"), 
                pm.get("password"), 
                pm.get("port"),
                pm.get("user"),
                self._body.get("memory")
            )
            if result:
                return pm
            else:
                self._pmachines.remove(pm)
        
        if org_len > 0:
            return jsonify(
                error_code=RET.NO_MEM_ERR,
                error_msg="the machine has no enough memory to use"
            )
   

        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg="No physical machine could be chosen.",
        )


class ChooseMirror(AuthMessageBody):
    def __init__(self, auth, body, api) -> None:
        super().__init__(auth, body)
        self._api = api

    def run(self, milestone):
        mirror = query_request(
            api=self._api,
            params={
                "milestone_id": milestone.get("id"),
                "frame": self._body.get("frame"),
            },
            auth=self.auth,
        )

        return mirror[0]


class Messenger:
    def __init__(self, auth, body, pmachine, api, method="put") -> None:
        self.auth = auth
        self._api = api
        self._body = body
        self._pmachine = pmachine
        self._method = method

    @abc.abstractmethod
    def handle_callback(self):
        pass

    def work(self):
        try:
            response = requests.request(
                self._method,
                "%s://%s:%d/%s"
                % (
                    current_app.config.get("PROTOCOL"),
                    self._pmachine.get("ip"),
                    self._pmachine.get("listen"),
                    self._api,
                ),
                data=json.dumps(self._body, cls=DateEncoder),
                headers={
                    "authorization": self.auth,
                    **current_app.config.get("HEADERS")
                },
            )
            resp = response.text.encode(response.encoding).decode(
                response.apparent_encoding
            )
            if response.status_code != 200:
                return jsonify(error_code=response.status_code, error_msg=resp)

            self._body.update({
                "pmachine_id": self._pmachine.get("id"),
            })

            resp_dict = json.loads(resp)
            
            return self.handle_callback(resp_dict)

        except requests.RequestException as e:
            current_app.logger.error(e)
            raise RecursionError(e)


class CeleryMessenger(Messenger):
    def handle_callback(self, resp_dict):
        celerytask_body = resp_dict.get("data")

        if not celerytask_body:
            return resp_dict

        celerytask_body.update({
            "state": "PENDING",
            "object_type": "vmachine",
            "vmachine_id": self._body.get("id"),
            "user_id": self._body.get("user_id"),
        })

        create_request(
            "/api/v1/celerytask",
            celerytask_body,
            self.auth
        )
        
        return self._body


class SyncMessenger(Messenger):
    def handle_callback(self, resp_dict):
        if resp_dict.get("error_code"):
            return resp_dict

        self._body.update({"pmachine_id": self._pmachine.get("id")})
        self._body.update(resp_dict)

        return self._body


def check_available_mem(ip, pwd, port, user, vm_mem):
    ssh = Connection(ip, pwd, port, user)
    conn = ssh._conn()
    if not conn:
        raise "failed to connect to physical machine."
    _, avail_mem = ssh._command("free -g | sed -n '2p' | awk '{print $7}'")
    ssh._close()
    return int(avail_mem) > int(vm_mem)/1024 + 5


class CreateVmachine(AuthMessageBody):
    def __init__(self, auth, body):
        self._pmachine = body.get("pmachine")
        self._product = body.get("product")
        self._milestone = body.get("milestone")
        self._update_milestone = None
        if body.get("update_milestone"):
            self._update_milestone = body.get("update_milestone")
        
        super().__init__(auth, body)

    def install(self):
        if self._body.get("pm_select_mode") == "auto":
            self._pmachine = ChoosePmachine(self.auth, self._body, choice).run()
            self._body.update({
                "pmachine": self._pmachine
            })

        elif self._body.get("pm_select_mode") == "assign":
            result = check_available_mem(
                self._pmachine.get("ip"), 
                self._pmachine.get("password"), 
                self._pmachine.get("port"),
                self._pmachine.get("user"),
                self._body.get("memory")
            )
            if not result:
                return jsonify(
                    error_code=RET.NO_MEM_ERR,
                    error_msg="the machine has no enough memory to use"
                )
        else:
            #预留其他方式
            pass
        if isinstance(self._pmachine, Response):
            return self._pmachine

        self._body.update({
            "pmachine_id": self._pmachine.get("id")
        })

        if self._body.get("method") == "import":
            mirror = ChooseMirror(
                self.auth,
                self._body, 
                "/api/v1/qmirroring"
            ).run(self._milestone)

            if mirror is None:
                self._body["method"] = "auto"
            else:
                self._body.update({
                    "url": mirror.get("url"),
                    "port": mirror.get("port"),
                    "user": mirror.get("user"),
                    "password": mirror.get("password"),
                })

        elif self._body.get("method") == "auto":
            mirror = ChooseMirror(
                self.auth,
                self._body, 
                "/api/v1/imirroring"
            ).run(self._milestone)

            if mirror is None:
                self._body["method"] = "cdrom"
            else:
                self._body.update(
                    {
                        "location": mirror.get("location"), 
                        "ks": mirror.get("ks")
                    }
                )

        elif self._body.get("method") == "cdrom":
            mirror = ChooseMirror(
                self.auth,
                self._body, 
                "/api/v1/imirroring"
            ).run(self._milestone)

            if mirror is None:
                return mirror

            self._body.update({"url": mirror.get("url")})

        if self._update_milestone:
            self._body.update(
                {
                    "host": self._pmachine.get("ip"),
                    "product": self._product.get("name") + " " + self._product.get("version"),
                    "milestone": self._milestone.get("name"),
                    "milestone_id": self._milestone.get("id"),
                    "update_milestone": self._update_milestone.get("name"),
                    "update_millestone_id": self._update_milestone.get("id"),
                    "status": "creating",
                }
            )
        else:
            self._body.update(
                {
                    "host": self._pmachine.get("ip"),
                    "product": self._product.get("name") + " " + self._product.get("version"),
                    "milestone": self._milestone.get("name"),
                    "milestone_id": self._milestone.get("id"),
                    "status": "creating",
                }
            )

        vmachine = create_request(
            "/api/v1/vmachine/data",
            self._body,
            self.auth
        )
        if not vmachine:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="fail to create vmachine data"
            )

        self._body.update(
            {
                "id": vmachine.get("id")
            }
        )

        self._body.update({"status": "installing"})

        resp = update_request(
            "/api/v1/vmachine/{}/data".format(
                self._body.get("id")
            ),
            {
                "status": self._body.get("status")
            },
            self.auth
        )
        if resp.get("error_code") != RET.OK:
            current_app.logger.warn(
                "fail to update the status of vmachine {}".format(
                    self._body.get("id")
                )
            )

        output = CeleryMessenger(
            self.auth,
            self._body,
            self._pmachine,
            "virtual/machine", "post"
        ).work()

        self._body.update(output)

        update_body = deepcopy(self._body)
        update_body.pop("id")

        resp = update_request(
            "/api/v1/vmachine/{}/data".format(
                self._body.get("id")
            ),
            update_body,
            self.auth
        )

        if resp.get("error_code") != RET.OK:
            current_app.logger.warn(
                "fail to update the status of vmachine {}".format(
                    self._body.get("id")
                )
            )
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "id": self._body.get("id")
            }
        )


class Control(AuthMessageBody):
    def __init__(self, auth, body) -> None:
        self._vmachine = body.get("vmachine")
        self._pmachine = self._vmachine.get("pmachine")
        body.update({"name": self._vmachine.get("name")})
        super().__init__(auth, body)

    def run(self):
        output = SyncMessenger(
            self.auth,
            self._body, 
            self._pmachine,
            "virtual/machine/power"
        ).work()

        if output.get("error_code"):
            return output

        self._body.update(output)

        if self._body.get("status") in ["start", "reset", "reboot"]:

            ip = QueryIp(self._vmachine.get("mac")).query()
            if isinstance(ip, dict):
                return ip

            if ip != self._vmachine.ip:
                self._body.update({"ip": ip})

        update_body = deepcopy(self._body)
        update_body.pop("id")

        resp = update_request(
            "/api/v1/vmachine/{}/data".format(
                self._body.get("id")
            ),
            update_body,
            self.auth
        )
        
        return jsonify(resp)


class DeleteVmachine(AuthMessageBody):
    def run(self):
        vmachine = self._body.get("vmachine")
        pmachine = self._body.get("pmachine")

        if pmachine:
            resp = SyncMessenger(
                self.auth,
                vmachine,
                pmachine,
                "virtual/machine",
                method="delete",
            ).work()

            if resp.get("error_code"):
                current_app.logger.debug(resp.get("error_msg"))
                return jsonify(
                    error_code=RET.DATA_DEL_ERR,
                    error_msg="vmachine {} fail to be deleted.".format(
                        vmachine.get("id")
                    )
                )

        if vmachine.get("vnc_port"):
            VncTokenCreator(pmachine.get("ip"), vmachine.get("vnc_port")).end()

        _r = do_request(
            method="delete",
            url="{}://{}/api/v1/vmachine/{}/force".format(
                current_app.config.get("PROTOCOL_TO_SERVER"),
                current_app.config.get("SERVER_ADDR"),
                vmachine.get("id")
            ),
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": self.auth
            },
        )

        if _r != 0:
            return jsonify(
                error_code=RET.DATA_DEL_ERR,
                error_msg="vmachine {} fail to be deleted.".format(
                    vmachine.get("id")
                )
            )
            
        return jsonify(
            error_code=RET.OK, 
            error_msg="vmachine success to delete."
        )


class DeviceManager(SyncMessenger):
    def add(self, target):
        self._vmachine = self._body.get("vmachine")
        self._pmachine = self._body.get("pmachine")
        self._body.update({"name": self._vmachine.get("name")})
        self._method = "post"

        resp = self.work()
        if resp.get("error_code"):
            return resp

        _url = None
        if target == "vnic":
            _url = "/api/v1/vnic/data"
        elif target == "vdisk":
            _url = "/api/v1/vdisk/data"

        device = create_request(
            _url,
            self._body,
            self.auth
        )

        if not device:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="fail to insert new device data"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    def delete(self, target):
        self._device = self._body.get("device")
        self._vmachine = self._body.get("vmachine")
        self._pmachine = self._body.get("pmachine")
        self._method = "delete"

        self._body.update(self._device)
        self._body.update({"name": self._vmachine.get("name")})

        resp = self.work()

        if resp.get("error_code"):
            return resp

        _url = None
        if target == "vnic":
            _url = "/api/v1/vnic/{}/data".format(self._device.get("id"))
        elif target == "vdisk":
            _url = "/api/v1/vdisk/{}/data".format(self._device.get("id"))

        _r = do_request(
            method="delete",
            url="{}://{}{}".format(
                current_app.config.get("PROTOCOL_TO_SERVER"),
                current_app.config.get("SERVER_ADDR"),
                _url
            ),
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": self.auth
            },
        )

        if _r != 0:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg="fail to delete device data"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    def attach(self):
        vmachine = self._body.get("vmachine")
        self._pmachine = vmachine.get("pmachine")
        self._body.update({"name": vmachine.get("name")})
        self._method = "post"

        resps = []

        for dv in self._body.get("device"):
            self._body.update({"xml": dv.get("device")})
            self._body.update({"service": dv.get("service")})

            resp = self.work()

            if resp and resp.get("error_code") == 0:
                if not vmachine.get("special_device"):
                    update_request(
                        "/api/v1/vmachine/{}/data".format(
                            vmachine.get("id")
                        ),
                        {
                            "special_device": self._body.get("service")
                        },
                        self.auth
                    )
                else:
                    update_request(
                        "/api/v1/vmachine/{}/data".format(
                            vmachine.get("id")
                        ),
                        {
                            "special_device": vmachine.get("special_device") + ',' + self._body.get("service")
                        },
                        self.auth
                    )

            resps.append(resp)

        return jsonify(resps)


class VmachineAsyncResultHandler:
    @staticmethod
    def edit(auth, body):
        pmachine = body.get("pmachine")

        _vnc_token = VncTokenCreator(
            pmachine.get("ip"), 
            body.get("vnc_port")
        ).start()

        body.update(
            {
                "vnc_token": _vnc_token,
            }
        )

        update_body = deepcopy(body)
        update_body.pop("id")

        resp = update_request(
            "/api/v1/vmachine/{}/data".format(
                body.get("id")
            ),
            update_body,
            auth
        )

        if body.get("method") == "cdrom":
            return jsonify(resp)

        pxe = QueryIp(body.get("mac"))

        for _ in range(current_app.config.get("VM_ENABLE_SSH")):
            ip = pxe.query()
            if isinstance(ip, Response):
                _r = do_request(
                    method="delete",
                    url="{}://{}/api/v1/vmachine/{}/force".format(
                        current_app.config.get("PROTOCOL_TO_SERVER"),
                        current_app.config.get("SERVER_ADDR"),
                        body.get("id")
                    ),
                    headers={
                        "content-type": "application/json;charset=utf-8",
                        "authorization": auth
                    },
                )

                if _r != 0:
                    return jsonify(
                        error_code=RET.SERVER_ERR,
                        error_msg="fail to delete vmachine"
                    )

                return ip

            ssh = Connection(ip, body.get("password"))
            conn = ssh._conn()
            if conn:
                break
            time.sleep(1)

        if not conn:
            mesg = "Failed to configure the repo source address."
            current_app.logger.warning(mesg)
            body.get("description") + " \n" + mesg

        body.update({"ip": ip})

        repo = query_request(
            "/api/v1/repo",
            {
                "milestone_id": body.get("milestone_id"),
                "frame": body.get("frame"),
            },
            auth
        )[0]

        update_repo = None
        if body.get("update_milestone_id"):
            update_repo = query_request(
                "/api/v1/repo",
                {
                    "milestone_id": body.get("update_milestone_id"),
                    "frame": body.get("frame"),
                },
                auth
            )[0]

        if repo:
            ssh._command(
                "mv /etc/yum.repos.d/openEuler.repo /etc/yum.repos.d/openEuler.repo.bak && echo -e '%s' > /etc/yum.repos.d/%s.repo"
                % (
                    repo.get("content"), 
                    body.get("milestone").replace(" ", "-")
                )
            )

        if update_repo:
            ssh._command(
                "echo -e '%s' > /etc/yum.repos.d/%s.repo"
                % (
                    update_repo.get("content"), 
                    body.get("update_milestone").name.replace(" ", "-")
                )
            )

        ssh._close()

        update_body = deepcopy(body)
        update_body.pop("id")

        resp = update_request(
            "/api/v1/vmachine/{}/data".format(
                body.get("id")
            ),
            update_body,
            auth
        )
        
        return jsonify(resp)
