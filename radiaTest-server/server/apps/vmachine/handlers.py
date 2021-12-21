import json
import time
from random import choice

from requests import request, RequestException
from flask import current_app, jsonify


from server.utils import DateEncoder
from server.utils.db import Delete, Edit, Precise, Insert, MultipleConditions
from server.utils.pssh import Connection
from server.utils.pxe import QueryIp
from server.utils.token_creator import VncTokenCreator

from server.model import Pmachine, Vmachine, IMirroring, QMirroring, Milestone, Repo


class MessageBody:
    def __init__(self, body) -> None:
        self._body = body


class ChoosePmachine(MessageBody):
    def __init__(self, body, algorithm) -> None:
        super().__init__(body)
        self._pmachine = Precise(
            Pmachine,
            {
                "frame": self._body.get("frame"),
                "description": current_app.config.get("CI_SIGN"),
                "state": "occupied",
            },
        ).all()
        self._algorithm = algorithm

    def run(self):
        if self._pmachine:
            return self._algorithm(self._pmachine)

        return {
            "error_code": 30005,
            "error_mesg": "No physical machine could be chosen.",
        }


class ChooseMirror(MessageBody):
    def __init__(self, body, table) -> None:
        super().__init__(body)
        self._table = table

    def run(self, milestone):
        mirroring = Precise(
            self._table,
            {
                "milestone_id": milestone.id,
                "frame": self._body.get("frame"),
            },
        ).first()

        if mirroring:
            return mirroring

        return {"error_code": 30006, "error_mesg": "No mirroring could be chosen."}


class Messenger:
    def __init__(self, body, pmachine, api, method="put") -> None:

        self._api = api
        self._body = body
        self._pmachine = pmachine
        self._method = method

    def work(self):
        try:
            response = request(
                self._method,
                "%s://%s:%d/%s"
                % (
                    current_app.config.get("PROTOCOL"),
                    self._pmachine.ip,
                    self._pmachine.listen,
                    self._api,
                ),
                data=json.dumps(self._body, cls=DateEncoder),
                headers=current_app.config.get("HEADERS"),
            )
            resp = response.text.encode(response.encoding).decode(
                response.apparent_encoding
            )
            if response.status_code != 200:
                return {"error_code": response.status_code, "error_mesg": resp}

            resp_dict = json.loads(resp)
            if resp_dict.get("error_code"):
                return resp_dict

            self._body.update({"pmachine_id": self._pmachine.id})
            self._body.update(resp_dict)

            return self._body
        except RequestException as e:
            current_app.logger.error(e)
            raise RecursionError(e)


class CreateVmachine(MessageBody):
    def install(self):
        pmachine = ChoosePmachine(self._body, choice).run()
        if isinstance(pmachine, dict):
            return pmachine

        _milestone = Milestone.query.filter_by(
            id=self._body.get("milestone_id")
        ).first()
        _update_milestone = None
        _product = _milestone.product

        if _milestone.type == "update":
            _update_milestone = _milestone
            _milestone = Precise(
                Milestone, {"product_id": _product.id, "type": "release"}
            ).first()

        if self._body.get("method") == "import":
            mirror = ChooseMirror(self._body, QMirroring).run(_milestone)
            if isinstance(mirror, dict):
                self._body["method"] = "auto"
            else:
                self._body.update({"url": mirror.url})

        elif self._body.get("method") == "auto":
            mirror = ChooseMirror(self._body, IMirroring).run(_milestone)
            if isinstance(mirror, dict):
                self._body["method"] = "cdrom"
            else:
                self._body.update({"location": mirror.location, "ks": mirror.ks})

        elif self._body.get("method") == "cdrom":
            mirror = ChooseMirror(self._body, IMirroring).run(_milestone)
            if isinstance(mirror, dict):
                return mirror
    
            self._body.update({"url": mirror.url})

        if _update_milestone:
            self._body.update(
                {
                    "host": pmachine.ip,
                    "product": _product.name + " " + _product.version,
                    "milestone": _update_milestone.name,
                    "status": "start create vm",
                    "pmachine_id": pmachine.id,
                }
            )
        else:
            self._body.update(
                {
                    "host": pmachine.ip,
                    "product": _product.name + " " + _product.version,
                    "milestone": _milestone.name,
                    "status": "start create vm",
                    "pmachine_id": pmachine.id,
                }
            )

        output = Insert(Vmachine, self._body).single(Vmachine, "/vmachine")
        if isinstance(output, dict):
            return output

        self._body.update(
            {"id": Precise(Vmachine, {"name": self._body.get("name")}).first().id}
        )

        self._body.update({"status": "installing"})
        output = Edit(Vmachine, self._body).single(Vmachine, "/vmachine")
        if isinstance(output, dict):
            Delete(Vmachine, {"name": self._body.get("name")}).single(
                Vmachine, "/vmachine"
            )
            return output

        output = Messenger(self._body, pmachine, "virtual/machine", "post").work()
        if output.get("error_code"):
            Delete(Vmachine, {"name": self._body.get("name")}).single(
                Vmachine, "/vmachine"
            )
            return jsonify(output)

        self._body.update(output)

        _vnc_token = VncTokenCreator(pmachine.ip, self._body.get("vnc_port")).start()

        self._body.update(
            {
                "vnc_token": _vnc_token,
                "websockify_listen": current_app.config.get("WEBSOCKIFY_LISTEN"),
            }
        )
        Edit(Vmachine, self._body).single(Vmachine, "/vmachine")
       
        if self._body.get("method") == "cdrom":
            return Edit(Vmachine, self._body).single(Vmachine, "/vmachine")
        
        pxe = QueryIp(self._body.get("mac"))
        for _ in range(current_app.config.get("VM_ENABLE_SSH")):
            ip = pxe.query()
            if isinstance(ip, dict):
                Delete(Vmachine, {"name": self._body.get("name")}).single(
                    Vmachine, "/vmachine"
                )
                return ip
            ssh = Connection(ip,"openEuler12#$")
            conn = ssh._conn()
            if conn:
                break
            time.sleep(1)
        if not conn:
                mesg = "Failed to configure the repo source address."
                current_app.logger.warning(mesg)
                self._body.get("description") + " \n" + mesg
        
        self._body.update({"ip": ip})

        repo = Precise(
            Repo,
            {
                "milestone_id": _milestone.id,
                "frame": self._body.get("frame"),
            },
        ).first()

        if _update_milestone:
            update_repo = Precise(
                    Repo,
                    {
                        "milestone_id": _update_milestone.id,
                        "frame": self._body.get("frame"),
                    },
                ).first()


        if repo:
            ssh._command(
                "mv /etc/yum.repos.d/openEuler.repo /etc/yum.repos.d/openEuler.repo.bak && echo -e '%s' > /etc/yum.repos.d/%s.repo"
                % (repo.content, _milestone.name.replace(" ", "-"))
            )

        if _update_milestone:
            update_repo = Precise(
                    Repo,
                    {
                        "milestone_id": _update_milestone.id,
                        "frame": self._body.get("frame"),
                    },
                ).first()
                
            if update_repo:
                ssh._command(
                            "echo -e '%s' > /etc/yum.repos.d/%s.repo"
                            % (update_repo.content, _update_milestone.name.replace(" ", "-"))
                        )

        ssh._close()

        return Edit(Vmachine, self._body).single(Vmachine, "/vmachine")


class Control(MessageBody):
    def __init__(self, body) -> None:
        super().__init__(body)
        self._vmachine = Precise(Vmachine, {"id": body.get("id")}).first()
        self._pmachine = self._vmachine.pmachine
        body.update({"name": self._vmachine.name})
        self._body = body

    def run(self):
        output = Messenger(self._body, self._pmachine, "virtual/machine/power").work()

        if output.get("error_code"):
            return output

        self._body.update(output)

        if self._body.get("status") in ["start", "reset", "reboot"]:

            ip = QueryIp(self._vmachine.mac).query()
            if isinstance(ip, dict):
                return ip

            if ip != self._vmachine.ip:
                self._body.update({"ip": ip})

        return Edit(Vmachine, self._body).single(Vmachine, "/vmachine")


class DeleteVmachine(MessageBody):
    def run(self):
        fail_del = []
        vmachines = MultipleConditions(Vmachine, self._body).all()
        if not vmachines:
            return jsonify(
                {
                    "error_code": 30005,
                    "error_mesg": "Those virtual machines have been deleted.",
                }
            )

        for vmachine in vmachines:
            pmachine = vmachine.pmachine
            if pmachine:
                resp = Messenger(
                    vmachine.to_json(),
                    pmachine,
                    "virtual/machine",
                    method="delete",
                ).work()

                if resp.get("error_code"):
                    current_app.logger.debug(resp.get("error_mesg"))
                    fail_del.append(vmachine.name)
                    continue

            if vmachine and vmachine.vnc_port:
                VncTokenCreator(pmachine.ip, vmachine.vnc_port).end()

            vmachine.delete(Vmachine, "/vmachine")

        if fail_del:
            return jsonify(
                {
                    "error_code": 30005,
                    "error_mesg": "Some virtual machines:%s fail to be deleted."
                    % fail_del,
                }
            )
        return jsonify({"error_code": 200, "error_mesg": "success to delete."})


class DeviceManager(Messenger):
    def add(self, table):
        vmachine = Precise(Vmachine, {"id": self._body.get("vmachine_id")}).first()
        self._pmachine = vmachine.pmachine
        self._body.update({"name": vmachine.name})
        self._method = "post"

        resp = self.work()
        if resp.get("error_code"):
            return resp

        return Insert(table, self._body).single(table, "/" + table.__name__.lower())

    def delete(self, table):
        device = Precise(table, self._body).first()
        vmachine = device.vmachine
        self._pmachine = vmachine.pmachine
        self._method = "delete"

        self._body.update(device.to_json())
        self._body.update({"name": vmachine.name})

        resp = self.work()

        if resp.get("error_code"):
            return resp

        return Delete(table, self._body).batch(table, "/" + table.__name__.lower())

    def attach(self):
        vmachine = Precise(Vmachine, {"id": self._body.get("vmachine_id")}).first()
        self._pmachine = vmachine.pmachine
        self._body.update({"name": vmachine.name})
        self._method = "post"

        resps = []

        for dv in self._body.get("device"):
            self._body.update({"xml": dv.get("device")})
            self._body.update({"service": dv.get("service")})

            resp = self.work()

            if resp and resp.get("error_code") == 0:
                if not vmachine.special_device:
                    Edit(
                        Vmachine, 
                        {
                            "id": vmachine.id,
                            "special_device": self._body.get("service"),
                        }
                    ).single(Vmachine, "/vmachine")
                else:
                    Edit(
                        Vmachine, 
                        {
                            "id": vmachine.id,
                            "special_device": vmachine.special_device + ',' + self._body.get("service"),
                        }
                    ).single(Vmachine, "/vmachine")
        
            resps.append(resp)
        
        return jsonify(resps)
        

def search_device(body, table):
    devices = table.query.filter_by(vmachine_id=body.get("vmachine_id")).all()
    return jsonify([data.to_json() for data in devices])