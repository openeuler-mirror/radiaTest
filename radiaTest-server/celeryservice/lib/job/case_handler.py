import time
import json
import random
import requests
from collections import defaultdict

from flask import current_app

from server import db
from celeryservice.lib import TaskAuthHandler
from server.utils.pssh import Connection
from server.utils.db import Insert, Precise
from server.model import (
    Vmachine,
    QMirroring,
    IMirroring,
    Pmachine,
    Analyzed,
    Vdisk,
    Vnic,
)
from server.model.milestone import Milestone
from server.model.testcase import Suite, Case
from server.apps.vmachine.handlers import DeleteVmachine, DeviceManager
from server.apps.pmachine.handlers import AutoInstall
from server.schema.vmachine import VmachineBase, VnicBase, VdiskBase
from server.model.framework import Framework, GitRepo
from server.apps.framework.adaptor import FrameworkAdaptor
from celeryservice.lib.job.logs_handler import LogsHandler
from celeryservice.lib.job.executor import Executor


class RunCaseHandler(TaskAuthHandler):
    def __init__(self, user, logger, promise, body):
        self._body = body
        self.promise = promise

        self.is_blocked = False
        self._root_name = self._body.get("name")
        self._name = self._root_name

        self._job_vmachines = defaultdict(list)

        super().__init__(user, logger)

    def vm_install_method(self):
        _milestone = Milestone.query.filter_by(
            id=self._body.get("milestone_id")
        ).first()

        if _milestone.type == "update":
            _milestone = Precise(
                Milestone, {
                    "product_id": _milestone.product.id,
                    "type": "release"
                }
            ).first()

        qcow2_mirror = QMirroring.query.filter_by(
            milestone_id=_milestone.id,
            frame=self._body.get("frame")
        ).first()

        iso_mirror = IMirroring.query.filter_by(
            milestone_id=_milestone.id,
            frame=self._body.get("frame")
        ).first()

        if qcow2_mirror:
            self._body.update({"method": "import"})
        elif iso_mirror:
            self._body.update({"method": "auto"})
        else:
            raise RuntimeError("Mirror is not registered.")

    def install_vmachine(self, quantity):
        self._body.update({"description": "used for CI job:%s" % self._name})

        # TODO 若Job名字可自定义，那么下方逻辑会产生变动
        for num in range(quantity):
            self._body.update({"name": self._name + "-" + str(num + 1)})

            _data = VmachineBase(**self._body).dict()
            _data.pop("end_time")

            output = requests.post(
                url="{}://{}:{}/api/v1/vmachine".format(
                    current_app.config.get("PROTOCOL"),
                    current_app.config.get("SERVER_IP"),
                    current_app.config.get("SERVER_PORT"),
                ),
                data=json.dumps(_data),
                headers={
                    'Content-Type': 'application/json;charset=utf8',
                    'Authorization': self.user.get("auth"),
                }
            )

            try:
                if output.status_code != 200:
                    raise Exception(output.text)

                resp_data = json.loads(output.text).get("data")
                self._job_vmachines["id"].append(resp_data.get("id"))

            except Exception as e:
                raise RuntimeError(
                    "Failed to create test machine, because: {}".format(
                        str(e)
                    )
                )

        times = 0
        while times < 30:
            num = 0
            db.session.commit()
            vmachines = Vmachine.query.filter_by(
                description=self._body.get("description")
            ).all()
            for vmachine in vmachines:
                if vmachine.ip is not None:
                    num += 1

            if num == quantity:
                return vmachines

            times += 1
            time.sleep(60)

        raise RuntimeError(
            "time out of limit for getting IP of job's machines"
        )

    def increase_vnic(self, machines, quantity):
        for machine in machines:
            for _ in range(quantity):
                output = DeviceManager(
                    VnicBase(**{"vmachine_id": machine.id}).dict(),
                    None,
                    "virtual/machine/vnic",
                ).add(Vnic)

                if output.json.get("error") != 200:
                    raise RuntimeError("Failed to increase network card.")

    def increase_vdisk(self, machines, capacities):
        for machine in machines:
            for capacity in capacities:
                output = DeviceManager(
                    VdiskBase(
                        **{"vmachine_id": machine.id, "capacity": capacity}
                    ).dict(),
                    None,
                    "virtual/machine/vdisk",
                ).add(Vdisk)

                if output.json.get("error") != 200:
                    raise RuntimeError("Failed to increase disk.")

    def install_pmachine(self, quantity):
        pmachines = Precise(
            Pmachine,
            {"description": current_app.config.get(
                "CI_PURPOSE"), "state": "idle"},
        ).all()

        if len(pmachines) < quantity:
            raise RuntimeError("Not enough Pmachines to be used")

        machines = random.choices(pmachines, k=quantity)
        for pmachine in machines:
            p_body = pmachine.to_json().update(
                {"milestone_id": self._body.get("milestone_id")}
            )

            output = AutoInstall(p_body).kickstart()
            if output.json.get("error") != 200:
                raise RuntimeError("Failed to install system os.")

        return machines

    def connect_master(self, machines):
        master = random.choice(machines)
        self._body.update({"master": master.ip})

        ssh = Connection(
            master.ip,
            master.password,
            master.port,
            master.user,
        )
        for _ in range(current_app.config.get("VM_ENABLE_SSH")):
            conn = ssh._conn()
            if conn:
                break

            time.sleep(1)

        if not conn:
            raise RuntimeError(
                "Can't establish a communication connection with master machine {}, job fail.".format(
                    master.ip,
                )
            )
        return ssh

    def work(self, machine_type, machine_num, add_network, add_disk, suites_cases):
        try:
            self.promise.update_state(
                state="PREPARING",
                meta={
                    "start_time": self.start_time,
                    "runnint_time": self.running_time,
                }
            )

            self._name = (
                self._root_name
                + '_m'
                + str(machine_num if machine_num else 0)
                + '_n'
                + str(add_network if add_network else 0)
                + '_d'
                + str(add_disk if add_disk else 0)
            )

            self.next_period()
            self.promise.update_state(
                state="INSTALLING",
                meta={
                    "start_time": self.start_time,
                    "runnint_time": self.running_time,
                },
            )

            if machine_type == "kvm":
                self.vm_install_method()
                machines = self.install_vmachine(machine_num)

                if add_network:
                    self.increase_vnic(machines, add_network)

                if add_disk:
                    self.increase_vdisk(machines, add_disk.split(","))

            elif machine_type == "physical":
                machines = self.install_pmachine(machine_num)
            else:
                raise RuntimeError(
                    "not support machine type: %s" % machine_type
                )

            self.next_period()
            self.promise.update_state(
                state="DEPLOYING",
                meta={
                    "start_time": self.start_time,
                    "runnint_time": self.running_time,
                }
            )

            ssh = self.connect_master(machines)

            try:
                git_repo = GitRepo.query.filter_by(
                    id=self._body.get("git_repo_id")
                ).first()
                framework = git_repo.framework
            except Exception as e:
                raise RuntimeError("valid framework or git repo is necessary")

            adaptor = getattr(FrameworkAdaptor, framework.name)

            _logs_handler = LogsHandler(
                ssh,
                self._body.get("id"),
                self._name,
                framework,
                adaptor
            )

            _executor = Executor(ssh, framework, git_repo, adaptor)

            _executor.prepare_git()
            _executor.deploy(self._body.get("master"), machines)

            self.next_period()
            self.promise.update_state(
                state="RUNNING",
                meta={
                    "start_time": self.start_time,
                    "runnint_time": self.running_time,
                }
            )

            success = 0
            fail = 0

            for suite_cases in suites_cases:
                testsuite = Suite.query.filter_by(name=suite_cases[0]).first()
                testcase = Case.query.filter_by(name=suite_cases[1]).first()
                if not testsuite or not testcase:
                    raise RuntimeError("testsuite {} or testcase {} is not exist".format(
                        suite_cases[0], 
                        suite_cases[1]
                    )
                )

                if testcase.usabled:
                    exitcode, output = _executor.run_test(
                        testcase.name,
                        testsuite.name,
                    )

                    self.logger.info(output)

                    _result = "success"
                    if exitcode:
                        _result = "fail"
                        fail += 1
                    else:
                        success += 1

                    self._body.update({
                        "success_cases": success,
                        "fail_cases": fail,
                    })
                    self.promise.update_state(
                        state="ANALYZING",
                        meta={
                            "start_time": self.start_time,
                            "runnint_time": self.running_time,
                            **self._body,
                        }
                    )

                    Insert(
                        Analyzed,
                        {
                            "result": _result,
                            "job_id": self._body.get("id"),
                            "case_id": testcase.id,
                            "master": self._body.get("master"),
                            # TODO logs_repo 这个表如果有必要存在，则写活
                            "log_url": "http://{}:{}/{}/{}/{}/{}/".format(
                                current_app.config.get("REPO_IP"),
                                current_app.config.get("REPO_PORT"),
                                current_app.config.get("LOGS_ROOT_URL"),
                                self._name,
                                testsuite.name,
                                testcase.name,
                            )
                        },
                    ).single(Analyzed, "/analyzed")

                    _logs_handler.push_dir_to_server()
                    # time.sleep(10)
                    _logs_handler.loads_to_db(testcase.id)

            ssh._close()
            self._body.update(
                {
                    "result": "success"
                    if len(suite_cases[1]) == success and fail == 0
                    else "fail",
                }
            )

        except RuntimeError as e:
            self.is_blocked = True

            self.logger.error(str(e))

            self._body.update({
                "result": "fail",
            })
            self.next_period()
            self.promise.update_state(
                state="BLOCK",
                meta={
                    "start_time": self.start_time,
                    "runnint_time": self.running_time,
                    **self._body,
                },
            )
            if (
                self._body.get("machine_type") == "kvm"
                and len(self._job_vmachines["id"]) > 0
            ):
                output = DeleteVmachine(self._job_vmachines).run()

                try:
                    # TODO  错误码统一后会产生修改
                    _r = output.json
                    if _r.get("error_code") != 200:
                        raise RuntimeError(_r.get("error_mesg"))
                except Exception as e:
                    self.logger.warn(
                        "Failed to delete vmachines: {}".format(
                            str(e)
                        )
                    )

        finally:
            if self._body.get("result") == "success" and len(self._job_vmachines["id"]) > 0:
                self.logger.warn(self._job_vmachines)
                output = DeleteVmachine(self._job_vmachines).run()

                try:
                    # TODO  错误码统一后会产生修改
                    _r = output.json
                    if _r.get("error_code") != 200:
                        raise RuntimeError(_r.get("error_mesg"))
                except Exception as e:
                    self.logger.warn(
                        "Failed to delete vmachines: {}".format(
                            str(e)
                        )
                    )

            if not self.is_blocked:
                self.next_period()
                self.promise.update_state(
                    state="DONE",
                    meta={
                        "start_time": self.start_time,
                        "runnint_time": self.running_time,
                        **self._body,
                    },
                )
