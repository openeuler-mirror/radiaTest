from datetime import datetime
import time
import json
import random
import requests
from collections import defaultdict

from flask import current_app

from celeryservice.lib import TaskAuthHandler
from celeryservice.lib.job.logs_handler import LogsHandler
from celeryservice.lib.job.executor import Executor
from server import db
from server.utils.pssh import Connection
from server.utils.db import Insert, Precise
from server.utils.response_util import RET
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
from server.schema.job import JobUpdateSchema
from server.model.framework import GitRepo
from server.model.job import Job
from server.apps.framework.adaptor import FrameworkAdaptor


class RunCaseHandler(TaskAuthHandler):
    def __init__(self, user, logger, promise, body):
        self._body = body
        self.promise = promise

        self.is_blocked = False
        self._root_name = self._body.get("name")
        self._name = self._root_name

        self._new_vmachines = defaultdict(list)
        self._borrow_pmachines = list()

        super().__init__(user, logger)

    def _create_job(self):
        if self._body.get("multiple") is False:
            self._update_job(
                name=self._name, 
                status="PREPARING",
            )
        else:
            parent = Job.query.filter_by(id=self._body.get("id")).first()
            if not parent:
                raise RuntimeError("parent job has already been deleted")

            self._body.update({
                "name": self._name,
                "start_time": self.start_time,
                "running_time":  0,
                "status": "PREPARING",
                "multiple": False,
            })
            self._body.pop("id")

            child_id = Insert(
                Job, 
                JobUpdateSchema(**self._body).dict()
            ).insert_id()

            job = Job.query.filter_by(id=child_id).first()
            if not job:
                raise RuntimeError(
                    "child job creating fail or has been deleted"
                )             
            
            job.parent.append(parent)
            job.add_update(Job, "/job", True)

            self._body.update(job.to_json())
            self._body.pop("milestone")

    def _update_job(self, **kwargs):
        self.next_period()
        self._body.update({
            "running_time": self.running_time,
            **kwargs,
        })
        
        job = Job.query.filter_by(id=self._body.get("id")).first()
        for key, value in self._body.items():
            setattr(job, key, value)
        
        job.add_update(Job, "/job", True)

    def get_vmachine(self, quantity):
        if self._body.get("machine_policy") == "auto":
            return [], self.install_vmachine(quantity)

        selected_machines = []
        new_machines = []
        self.logger.warn(self._body)
        for vmachine_id in self._body.get("vmachine_list"):
            vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
            if not vmachine:
                self.logger.info(f"vmachine {vmachine_id} not exist, a new vmachine will be created instead.")
                continue

            selected_machines.append(vmachine)

        if self._body.get("machine_policy") == "manual":
            rest_quantity = quantity - len(self._body.get("vmachine_list"))

            if rest_quantity > 0:
                new_machines = self.install_vmachine(rest_quantity)
        else:
            raise RuntimeError(
                "unsupported machine select policy: {}".format(
                    self._body.get("machine_policy")
                )
            )

        if len(selected_machines) + len(new_machines) < quantity:
            raise RuntimeError(
                "could not satisfy the require number of vmachiens"
            )
        
        return selected_machines, new_machines

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
        self.vm_install_method()

        self._body.update({"description": "used for CI job:%s" % self._name})

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
                    raise RuntimeError(output.text)

                resp_data = json.loads(output.text).get("data")
                self._new_vmachines["id"].append(resp_data.get("id"))

            except (AttributeError, RuntimeError, TypeError) as e:
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

    def get_pmachine(self, quantity, pmachine_pool):
        if self._body.get("machine_policy") == "auto":
            return [], self.install_pmachine(quantity, pmachine_pool)

        selected_machines = []
        new_machines = []
        for pmachine_id in self._body.get("pmachine_list"):
            pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
            if not pmachine:
                continue

            selected_machines.append(pmachine)
        
        if self._body.get("machine_policy") == "manual":
            rest_quantity = quantity - len(self._body.get("pmachine_list"))

            if rest_quantity > 0:
                new_machines = self.install_pmachine(rest_quantity)
        else:
            raise RuntimeError(
                "unsupported machine select policy: {}".format(
                    self._body.get("machine_policy")
                )
            )

        if len(selected_machines) + len(new_machines) < quantity:
            raise RuntimeError(
                "could not satisfy the require number of vmachiens"
            )
        
        return selected_machines, new_machines

    def install_pmachine(self, quantity, pmachine_pool):
        if len(pmachine_pool) < quantity:
            raise RuntimeError(
                "Not enough Pmachines to be used, {} is still needed but only {} could be offered".format(
                    quantity, 
                    len(pmachine_pool)
                )
            )

        pmachine_ids = random.choices(pmachine_pool, k=quantity)
        # celery化，改为异步，chord task
        for pmachine_id in pmachine_ids:
            pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
            if not pmachine:
                raise RuntimeError(
                    f"Failed to install system os, because pmachine {pmachine_id} not exist."
                )

            pmachine.locked = True
            pmachine.add_update(Pmachine, "/pmachine", True)

            p_body = pmachine.to_json().update(
                {"milestone_id": self._body.get("milestone_id")}
            )

            output = AutoInstall(p_body).kickstart()
            if output.json.get("error") != 200:
                raise RuntimeError("Failed to install system os.")

            # chord callback
            self._borrow_pmachines.append(pmachine)

        return self._borrow_pmachines

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

    def work(self, env_params, suites_cases, pmachine_pool):
        try:
            machine_num = env_params.get("machine_num")
            machine_type = env_params.get("machine_type")
            add_network = env_params.get("add_network")
            add_disk = env_params.get("add_disk")

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
                "total": len(suites_cases)
            })

            self._create_job()

            self._update_job(status="INSTALLING")

            if machine_type == "kvm":
                selected_machines, new_machines = self.get_vmachine(machine_num)

                if add_network:
                    self.increase_vnic(new_machines, add_network)

                if add_disk:
                    self.increase_vdisk(new_machines, add_disk.split(","))

            elif machine_type == "physical":
                selected_machines, new_machines = self.get_pmachine(
                    machine_num, 
                    pmachine_pool
                )
            else:
                raise RuntimeError(
                    "not support machine type: %s" % machine_type
                )

            machines = selected_machines + new_machines

            self._update_job(status="SELECTING")

            ssh = self.connect_master(machines)

            self._update_job(status="DEPLOYING")

            try:
                git_repo = GitRepo.query.filter_by(
                    id=self._body.get("git_repo_id")
                ).first()
                framework = git_repo.framework
            except AttributeError as e:
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

            self._update_job(status="TESTING")

            success = 0
            fail = 0

            for suite_cases in suites_cases:
                _start_time = datetime.now()

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
                    self._update_job(status="ANALYZING")

                    _current_time = datetime.now()

                    _running_time = (_current_time - _start_time).seconds * 1000 + (_current_time - _start_time).microseconds/1000

                    Insert(
                        Analyzed,
                        {
                            "result": _result,
                            "job_id": self._body.get("id"),
                            "case_id": testcase.id,
                            "master": self._body.get("master"),
                            "log_url": "http://{}:{}/{}/{}/{}/{}/".format(
                                current_app.config.get("REPO_IP"),
                                current_app.config.get("REPO_PORT"),
                                current_app.config.get("LOGS_ROOT_URL"),
                                self._name,
                                testsuite.name,
                                testcase.name,
                            ),
                            "running_time": _running_time,
                        },
                    ).single(Analyzed, "/analyzed")

                    _logs_handler.push_dir_to_server()
                    _logs_handler.loads_to_db(testcase.id)

            ssh._close()
            self._body.update(
                {
                    "result": "success"
                    if self._body.get("total") == success and fail == 0
                    else "fail",
                }
            )

        except RuntimeError as e:
            self.is_blocked = True

            self.logger.error(str(e))

            self._update_job(
                result="fail",
                remark=str(e),
                status="BLOCK", 
                end_time=datetime.now()
            )

            if (
                self._body.get("machine_type") == "kvm"
                and len(self._new_vmachines["id"]) > 0
            ):
                output = DeleteVmachine(self._new_vmachines).run()

                try:
                    _r = output.json
                    if _r.get("error_code") != RET.OK:
                        raise RuntimeError(_r.get("error_mesg"))
                except (AttributeError, TypeError, RuntimeError) as e:
                    self.logger.warn(
                        "Failed to delete vmachines: {}".format(
                            str(e)
                        )
                    )

        finally:
            if self._body.get("result") == "success" and len(self._new_vmachines["id"]) > 0:
                output = DeleteVmachine(self._new_vmachines).run()

                try:
                    _r = output.json
                    if _r.get("error_code") != RET.OK:
                        raise RuntimeError(_r.get("error_mesg"))
                except (AttributeError, TypeError, RuntimeError) as e:
                    self.logger.warn(
                        "Failed to delete vmachines: {}".format(
                            str(e)
                        )
                    )
            
            if len(self._borrow_pmachines) > 0:
                for _borrow_pmachine in self._borrow_pmachines:
                    _borrow_pmachine.locked = False
                    _borrow_pmachine.add_update(Pmachine, "/pmachine", True)

            if not self.is_blocked:
                self._update_job(status="DONE", end_time=datetime.now())

            return {
                "name": self._body.get("name"),
                "status": self._body.get("status"),
                "result": self._body.get("result"),
                "remark": self._body.get("remark"),
                "running_time": self._body.get("running_time"),
                "success_cases": self._body.get("success_cases"),
                "fail_cases": self._body.get("fail_cases"),
            }
