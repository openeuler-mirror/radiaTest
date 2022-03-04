import json
import time
import random
import requests
from datetime import datetime

from flask_socketio import SocketIO
from flask import current_app, jsonify

from server import db
from server.utils.pssh import Connection
from server.utils.db import Edit, Insert, Like, Precise
from server.model import (
    Job,
    Vmachine,
    Suite,
    QMirroring,
    IMirroring,
    Pmachine,
    Analyzed,
    Case,
    Vdisk,
    Vnic,
)
from server.model.milestone import Milestone
from server.model.task import TaskMilestone
from server.apps.job.executor import Executor
from server.model.framework import Framework, GitRepo
from server.apps.framework.adaptor import FrameworkAdaptor
from server.apps.job.logs_handler import LogsHandler
from server.apps.vmachine.handlers import CreateVmachine, DeleteVmachine, DeviceManager
from server.apps.pmachine.handlers import AutoInstall
from server.schema.vmachine import VmachineBase, VnicBase, VdiskBase


class RunJob:
    def __init__(self, body) -> None:
        self._body = body
        self._root_name = self._body.get("name")
        self._name = self._root_name

    def install_method(self):
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

    def install_vm(self, quantity):
        self._body.update({"description": "used for CI job:%s" % self._name})
        for num in range(quantity):
            self._body.update({"name": self._name + "-" + str(num + 1)})
            output = CreateVmachine(VmachineBase(
                **self._body).dict()).install()

            if output.json.get("error_code") != 200:
                raise RuntimeError("Failed to create test machine.")

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
            "time out of limit for getting IP of job's machines")

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

    def install_physical(self, quantity):
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
                "Can't establish a communication connection with the tester, please contact the administrator."
            )
        return ssh

    def _create_job(self):
        self._body.update({"status": "preparing"})
        if self._body.get("id"):
            del self._body["id"]
        output = Insert(Job, self._body).single(Job, "/job")
        if output.json.get("error_code") != 200:
            raise RuntimeError(
                "Failed to create job for template:%s."
                % self._template.name
            )
        return Precise(Job, {"name": self._name}).first()


class RunSuite(RunJob):
    def run(self):
        try:
            self._job = self._create_job()
            self._body.update(self._job.to_json())
            self._body.pop("milestone")

            suite = Precise(
                Suite, {"name": self._body.get("testsuite")}).first()
            if not suite:
                raise RuntimeError(
                    "The test suite:%s does not exist, please contact the tester to add it in time."
                )

            self._body.update({
                "status": "installing",
                "total": len(
                    Case.query.filter_by(
                        suite_id=suite.id,
                        usabled=True,
                    ).all()
                ),
                "success_cases": 0,
                "fail_cases": 0,
            })
            Edit(Job, self._body).single(Job, '/job')

            self.install_method()

            if suite.machine_type == "kvm":
                machines = self.install_vm(suite.machine_num)

                if suite.add_network_interface:
                    self.increase_vnic(suite.add_network_interface)

                if suite.add_disk:
                    self.increase_vdisk(suite.add_disk.split(","))

            elif suite.machine_type == "physical":
                machines = self.install_physical(suite.machine_num)
            else:
                raise RuntimeError("not support %s" % suite.machine_type)

            self._body.update({"status": "deploying"})
            Edit(Job, self._body).single(Job, '/job')

            ssh = self.connect_master(machines)

            framework = Framework.query.filter_by(
                name="mugen"
            ).first()

            adaptor = getattr(FrameworkAdaptor, framework.name)

            git_repo = GitRepo.query.filter_by(name="mugen").first()

            _executor = Executor(
                ssh, framework, git_repo, adaptor
            )
            _logs_handler = LogsHandler(
                ssh,
                self._body.get("id"),
                self._name,
                framework,
                adaptor
            )

            _executor.prepare_git()

            _executor.deploy(self._body.get("master"), machines)

            self._body.update({"status": "testing"})
            Edit(Job, self._body).single(Job, '/job')

            success = 0
            fail = 0
            for case in suite.case:
                if case.usabled:
                    exitcode, output = _executor.run_test(
                        testcase=case.name,
                        testsuite=suite.name,
                    )
                    current_app.logger.info(output)
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
                    Edit(Job, self._body).single(Job, '/job')

                    Insert(
                        Analyzed,
                        {
                            "result": _result,
                            "job_id": self._body.get("id"),
                            "case_id": case.id,
                            "master": self._body.get("master"),
                            "log_url": "http://{}:{}/{}/{}/{}/{}/".format(
                                current_app.config.get("REPO_IP"),
                                current_app.config.get("REPO_PORT"),
                                current_app.config.get("LOGS_ROOT_URL"),
                                self._name,
                                suite.name,
                                case.name,
                            )
                        },
                    ).single(Analyzed, "/analyzed")

                    _logs_handler.push_dir_to_server()
                    time.sleep(10)
                    _logs_handler.loads_to_db(case.id)

            ssh._close()
            self._body.update(
                {
                    "result": "success"
                    if len(suite.case) == success and fail == 0
                    else "fail",
                }
            )

        except RuntimeError as e:
            self._body.update({
                "status": "block",
                "result": "fail",
            })
            if (
                self._body.get("machine_type") == "kvm"
                and Like(Vmachine, {"name": self._name}).all()
            ):
                DeleteVmachine(self._body).run()
            return jsonify({"error_code": 60009, "error_mesg": str(e)})

        finally:
            if self._body.get("result") == "success":
                DeleteVmachine(self._body).run()

            if self._body.get("status") != "block":
                self._body.update({
                    "status": "done",
                    "end_time": datetime.now(),
                    "result": self._body.get("result"),
                })

            Edit(Job, self._body).single(Job, "/job")


class RunTemplate(RunJob):
    def __init__(self, body) -> None:
        super().__init__(body)
        self._template = self._body.pop("template")

        for key in list(self._body.keys()):
            if not self._body.get(key):
                del self._body[key]
        if not self._body.get("milestone_id"):
            self._body.update({"milestone_id": self._template.milestone_id})

    def _sort(self):
        cases = self._template.cases
        if not cases:
            raise RuntimeError("Template unbound use case.")

        machine_type = []
        machine_num = []
        add_network = []
        add_disk = []
        for case in cases:
            machine_type.append(case.machine_type)
            machine_num.append(case.machine_num)
            add_network.append(case.add_network_interface)
            add_disk.append(case.add_disk)
        machine_type = list(set(machine_type))
        machine_num = list(set(machine_num))
        add_network = list(set(add_network))
        add_disk = list(set(add_disk))

        classify_cases = []
        for m_type in machine_type:
            for machine in machine_num:
                for network in add_network:
                    for disk in add_disk:
                        cs = {}
                        cl = []
                        for case in cases:
                            if (
                                case.machine_num == machine
                                and case.add_network_interface == network
                                and case.add_disk == disk
                            ):
                                cl.append([case.suite.name, case.name])

                        if cl:
                            cs["type"] = m_type
                            cs["machine"] = machine
                            cs["network"] = network
                            cs["disk"] = disk
                            cs["cases"] = cl
                            classify_cases.append(cs)

        return classify_cases

    def _run_case(self, machine_type, machine_num, add_network, add_disk, cases):
        try:
            self._name = (
                self._root_name
                + '_m'
                + str(machine_num if machine_num else 0)
                + '_n'
                + str(add_network if add_network else 0)
                + '_d'
                + str(add_disk if add_disk else 0)
            )

            self._body.update({
                "status": "installing"
            })
            Edit(Job, self._body).single(Job, '/job')

            self.install_method()

            if machine_type == "kvm":
                machines = self.install_vm(machine_num)

                if add_network:
                    self.increase_vnic(machines, add_network)

                if add_disk:
                    self.increase_vdisk(machines, add_disk.split(","))

            elif machine_type == "physical":
                machines = self.install_physical(machine_num)
            else:
                raise RuntimeError("not support %s" % machine_type)

            self._body.update({
                "status": "deploying"
            })
            Edit(Job, self._body).single(Job, '/job')

            ssh = self.connect_master(machines)

            framework = Framework.query.filter_by(
                name=self._body.get("framework")
            ).first()

            adaptor = getattr(FrameworkAdaptor, self._body.get("framework"))

            _executor = Executor(ssh, framework, adaptor)
            _logs_handler = LogsHandler(
                ssh,
                self._body.get("id"),
                self._name,
                framework,
                adaptor
            )

            _executor.prepare_git()
            _executor.deploy(self._body.get("master"), machines)

            self._body.update({
                "status": "testing"
            })
            Edit(Job, self._body).single(Job, '/job')

            for case in cases:
                suite = Precise(Suite, {"name": case[0]}).first()
                testcase = Precise(
                    Case, {"suite_id": suite.id, "name": case[1]}
                ).first()
                exitcode, output = _executor.run_test(
                    testcase=case[1],
                    testsuite=case[0],
                )
                current_app.logger.info(output)
                if exitcode:
                    result = "fail"
                    self._body.update({
                        "fail_cases": self._body.get("fail_cases") + 1
                    })
                    Edit(Job, self._body).single(Job, '/job')

                else:
                    result = "success"
                    self._body.update({
                        "success_cases": self._body.get("success_cases") + 1
                    })
                    Edit(Job, self._body).single(Job, '/job')

                Insert(
                    Analyzed,
                    {
                        "result": result,
                        "job_id": self._body.get("id"),
                        "case_id": testcase.id,
                        "master": self._body.get("master"),
                        "log_url": "http://{}:{}/{}/{}/logs/{}/{}/".format(
                            current_app.config.get("REPO_IP"),
                            current_app.config.get("REPO_PORT"),
                            current_app.config.get("LOGS_ROOT_URL"),
                            self._name,
                            case[0],
                            case[1],
                        )
                    },
                ).single(Analyzed, "/analyzed")

                _logs_handler.push_dir_to_server()
                time.sleep(10)
                _logs_handler.loads_to_db(testcase.id)

        except RuntimeError as e:
            self._body.update({
                "status": "block",
                "result": "fail",
                "end_time": datetime.now()
            })
            Edit(Job, self._body).single(Job, '/job')

            DeleteVmachine(self._body).run()
            raise RuntimeError(e)

    def _callback_task_job_init(self):
        return Edit(
            TaskMilestone,
            {
                "id": self._body.get("taskmilestone_id"),
                "job_id": self._job.id
            }
        ).single()

    def _callback_task_job_result(self):
        try:
            resp = requests.put(
                url="{}://{}:{}/api/v1/task/milestones/{}".format(
                    current_app.config.get("PROTOCOL"),
                    current_app.config.get("SERVER_IP"),
                    current_app.config.get("SERVER_PORT"),
                    self._body.get("taskmilestone_id")
                ),
                data=json.dumps({
                    "job_id": self._body.get("id"),
                    "result": self._body.get("status"),
                }),
                headers=current_app.config.get("HEADERS")
            )
            resp.encoding = resp.apparent_encoding

            if resp.status_code == 200:
                current_app.logger.info(
                    "Task job has been call back => " + resp.text)
            else:
                current_app.logger.error(
                    "Error in calling back to TaskMilestones => " + resp.text)
        except Exception as e:
            current_app.logger.error(
                "Error in calling back to TaskMilestones => " + str(e))

    def run(self):
        try:
            self._job = self._create_job()
            self._body.update(self._job.to_json())
            self._body.pop("milestone")

            if self._job and self._body.get("taskmilestone_id"):
                resp = self._callback_task_job_init()
                if resp.status_code != 200:
                    current_app.logger.error(
                        "Cannot callback job_id to taskmilestone table: " + resp.error_mesg)

            self._body.update({
                "status": "preparing",
                "total": len(self._template.cases),
                "success_cases": 0,
                "fail_cases": 0,
            })
            Edit(Job, self._body).single(Job, '/job')

            classify_cases = self._sort()

            for cases in classify_cases:
                self._run_case(
                    cases.get("type"),
                    cases.get("machine"),
                    cases.get("network"),
                    cases.get("disk"),
                    cases.get("cases"),
                )

            _result = "fail"

            if self._body.get("total") == self._body.get("success_cases"):
                _result = "success"

            self._body.update({
                "status": "done",
                "result": _result,
                "end_time": datetime.now()
            })
            Edit(Job, self._body).single(Job, '/job')

        except RuntimeError as e:
            if not self._job:
                return jsonify({"error_code": 60009, "error_mesg": str(e)})

            self._body.update({
                "result": "fail",
                "status": "block",
                "remark": str(e),
                "end_time": datetime.now()
            })
            Edit(Job, self._body).single(Job, "/job")

            return jsonify({"error_code": 60009, "error_mesg": str(e)})

        finally:
            if self._body.get("taskmilestone_id"):
                self._callback_task_job_result()
