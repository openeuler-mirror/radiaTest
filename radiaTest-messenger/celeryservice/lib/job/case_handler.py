import os
from copy import deepcopy
import json
import datetime
import time
import random
import collections
from collections import defaultdict
import pytz

from flask import current_app

from celeryservice import celeryconfig
from celeryservice.lib import TaskAuthHandler
from celeryservice.lib.adapter.log_resolver_adapter import LogResolverAdapter
from celeryservice.lib.adapter.executor_adapter import ExecutorAdaptor
from messenger.utils.pssh import ConnectionApi
from messenger.utils.requests_util import create_request, do_request, query_request, update_request
from messenger.utils.response_util import RET
from messenger.apps.vmachine.handlers import DeleteVmachine, DeviceManager, RequestWorkerParam, MachineInfoParam
from messenger.apps.pmachine.handlers import AutoInstall
from messenger.schema.vmachine import VmachineBaseSchema, VmachineCreateSchema, VnicBaseSchema, VdiskBaseSchema
from messenger.schema.job import JobCreateSchema, JobUpdateSchema
from celeryservice.lib.framework import FrameworkDict


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
            parent = query_request(
                "/api/v1/job/{}".format(
                    self._body.get("id")
                ),
                None,
                self.user.get("auth")
            )

            if not parent:
                raise RuntimeError("parent job has already been deleted")

            self._body.update({
                "name": self._name,
                "start_time": self.start_time,
                "running_time": 0,
                "status": "PREPARING",
                "multiple": False,
            })
            self._body.pop("id")

            child = create_request(
                "/api/v1/job",
                {
                    "parent_id": parent.get("id"),
                    **JobCreateSchema(**self._body).dict()
                },
                self.user.get("auth")
            )

            if not child:
                raise RuntimeError(
                    "child job creating fail or has been deleted"
                )

            self._body.update(child)
            self._body.pop("milestone")

    def _update_job(self, **kwargs):
        self.next_period()
        self._body.update({
            "running_time": self.running_time,
            **kwargs,
        })

        update_body = deepcopy(self._body)
        _job_id = update_body.pop("id")

        _resp = update_request(
            "/api/v1/job/{}".format(
                _job_id
            ),
            update_body,
            self.user.get("auth")
        )
        if not _resp:
            raise RuntimeError("jwt token might be overdue, try again")

    def get_vmachine(self, quantity):
        if self._body.get("machine_policy") == "auto":
            return [], self.install_vmachine(quantity)

        new_machines = []
        self.logger.info(self._body.get("vmachine_list"))
        selected_machines = self._body.get("vmachine_list")

        if self._body.get("machine_policy") == "manual":
            rest_quantity = quantity - len(selected_machines)

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
        _milestone = query_request(
            "/api/v2/milestone/{}".format(
                self._body.get("milestone_id")
            ),
            None,
            self.user.get("auth")
        )

        if not _milestone:
            raise RuntimeError("cannot get milestone data")

        if _milestone.get("type") == "update":
            _milestone = query_request(
                "/api/v1/milestone/preciseget",
                {
                    "product_id": _milestone.get("product_id"),
                    "type": "release"
                },
                self.user.get("auth"),
            )[0]

        qcow2_mirror = query_request(
            "/api/v1/qmirroring/preciseget",
            {
                "milestone_id": _milestone.get("id"),
                "frame": self._body.get("frame")
            },
            self.user.get("auth"),
        )

        iso_mirror = query_request(
            "/api/v1/imirroring/preciseget",
            {
                "milestone_id": _milestone.get("id"),
                "frame": self._body.get("frame")
            },
            self.user.get("auth"),
        )

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

            _data = VmachineCreateSchema(**self._body).dict()
            _data.pop("end_time")

            resp_data = create_request(
                "/api/v1/vmachine",
                _data,
                self.user.get("auth")
            ) 

            self._new_vmachines["id"].append(resp_data.get("id"))

        times = 0
        while times < 30:
            num = 0
            vmachines = query_request(
                "/api/v1/vmachine/preciseget",
                {
                    "description": self._body.get("description")
                },
                self.user.get("auth")
            )

            for vmachine in vmachines:
                if vmachine.get("ip") is not None:
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
                request_worker_param = RequestWorkerParam(
                    self.user.get("auth"),
                    VnicBaseSchema(**{"vmachine_id": machine.id}).dict(),
                    "virtual/machine/vnic"
                )
                machine_info_param = MachineInfoParam()

                DeviceManager(request_worker_param, machine_info_param).add("vnic")

    def increase_vdisk(self, machines, capacities):
        for machine in machines:
            for capacity in capacities:
                request_worker_param = RequestWorkerParam(
                    self.user.get("auth"),
                    VdiskBaseSchema(
                        **{"vmachine_id": machine.id, "capacity": capacity}
                    ).dict(),
                    "virtual/machine/vdisk"
                )
                machine_info_param = MachineInfoParam()

                DeviceManager(request_worker_param, machine_info_param).add("vdisk")

    def get_pmachine(self, quantity, pmachine_pool):
        if self._body.get("machine_policy") == "auto":
            return [], self.install_pmachine(quantity, pmachine_pool)

        new_machines = []
        selected_machines = self._body.get("pmachine_list")

        if self._body.get("machine_policy") == "manual":
            rest_quantity = quantity - len(selected_machines)

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

        pmachines = random.choices(pmachine_pool, k=quantity)

        for pmachine in pmachines:
            pmachine["locked"] = True
            update_request(
                "/api/v1/pmachine/{}".format(
                    pmachine.get("id")
                ),
                {
                    "locked": True
                },
                self.user.get("auth")
            )

            p_body = pmachine.update(
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
        self._body.update({"master": master.get("ip")})

        ssh = ConnectionApi(
            master.get("ip"),
            master.get("password"),
            master.get("port"),
            master.get("user"),
        )
        for _ in range(current_app.config.get("VM_ENABLE_SSH")):
            conn = ssh.conn()
            if conn:
                break

            time.sleep(1)

        if not conn:
            raise RuntimeError(
                "Can't establish a communication connection with master machine {}, job fail.".format(
                    master.get("ip"),
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
            
            git_repo = query_request(
                "/api/v1/git-repo/{}".format(
                    self._body.get("git_repo_id")
                ),
                None,
                self.user.get("auth")
            )

            framework = git_repo.get("framework")

            adaptor = getattr(FrameworkDict, framework.get("name"))

            LogresolverParam = collections.namedtuple(
                'LogresolverParam',
                [
                    'ssh',
                    'id',
                    'name',
                    'framework',
                    'adaptor',
                    'auth'
                ]
            )
            log_resolver_param = LogresolverParam(
                ssh,
                self._body.get('id'),
                self._name, framework,
                adaptor.logresolver(),
                self.user.get("auth")
            )

            _logs_handler = LogResolverAdapter(log_resolver_param)

            _executor = ExecutorAdaptor(ssh, framework, git_repo, adaptor.executor())

            _executor.prepare_git()
            _executor.deploy(self._body.get("master"), machines)

            self._update_job(status="TESTING")

            success = 0
            fail = 0

            for suite_cases in suites_cases:
                _start_time = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))

                testsuite = query_request(
                    "/api/v1/suite/preciseget",
                    {
                        "name": suite_cases[0]
                    },
                    self.user.get("auth")
                )

                testcase = query_request(
                    "/api/v1/case/preciseget",
                    {
                        "name": suite_cases[1]
                    },
                    self.user.get("auth")
                )

                if not testsuite or not testcase:
                    raise RuntimeError("testsuite {} or testcase {} is not exist".format(
                        suite_cases[0],
                        suite_cases[1]
                    )
                    )

                testsuite = testsuite[0]
                testcase = testcase[0]

                if testcase.get("usabled"):
                    exitcode, output = _executor.run_test(
                        testcase.get("name"),
                        testsuite.get("name"),
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

                    _current_time = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))

                    _running_time = (_current_time - _start_time).seconds * 1000 + (
                            _current_time - _start_time).microseconds / 1000

                    create_request(
                        "/api/v1/analyzed",
                        {
                            "result": _result,
                            "job_id": self._body.get("id"),
                            "case_id": testcase.get("id"),
                            "master": self._body.get("master"),
                            "log_url": os.path.join(
                                current_app.config.get("REPO_URL"),
                                self._name,
                                testsuite.get("name"),
                                testcase.get("name"),
                                ""
                            ),
                            "running_time": _running_time,
                        },
                        self.user.get("auth")
                    )

                    _logs_handler.push_dir_to_server()
                    _logs_handler.loads_to_db(testcase.get("id"))

            ssh.close()
            self._body.update(
                {
                    "result": "success"
                    if self._body.get("total") == success and fail == 0
                    else "fail",
                }
            )

        except (RuntimeError, ValueError) as e:
            current_app.logger.error(e)
            self.is_blocked = True

            self.logger.error(str(e))

            self._update_job(
                result="fail",
                remark=str(e),
                status="BLOCK",
                end_time=datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
            )

            if (
                    self._body.get("machine_type") == "kvm"
                    and len(new_machines) > 0
            ):
                resp = DeleteVmachine(self.user.get("auth"), new_machines).run()
                resp = json.loads(resp.data.decode('UTF-8'))
                if resp.get("error_code") != RET.OK:
                    raise RuntimeError(resp.get("error_msg"))

        finally:
            if self._body.get("result") == "success" and len(new_machines) > 0 and machine_type == "kvm":
                self._new_vmachines.update(
                    {
                        "end_time": datetime.datetime.now(
                            tz=pytz.timezone('Asia/Shanghai')
                        )
                        + datetime.timedelta(
                            days=current_app.config.get("RUN_JOB_VM_EXPIRED")
                        )
                    }
                )
                r = do_request(
                    method="put",
                    url="https://{}/api/v1/vmachine/batch/delay".format(
                        celeryconfig.server_addr,
                    ),
                    body=self._new_vmachines,
                    headers={
                        "authorization": self.user.get("auth"),
                        "content-type": "application/json;charset=utf-8",
                    },
                    verify=True if celeryconfig.ca_verify == "True" \
                        else celeryconfig.cacert_path
                )
                if r != 0:
                    self.logger.warning(
                        "fail to batch delay virtual machines of success job"
                    )

            if len(self._borrow_pmachines) > 0:
                for _borrow_pmachine in self._borrow_pmachines:
                    _borrow_pmachine["locked"] = False
                    update_request(
                        "/api/v1/pmachine/{}".format(
                            _borrow_pmachine.get("id")
                        ),
                        {
                            "locked": False
                        },
                        self.user.get("auth")
                    )

            if not self.is_blocked:
                self._update_job(
                    status="DONE",
                    end_time=datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
                )

            return {
                "name": self._body.get("name"),
                "status": self._body.get("status"),
                "result": self._body.get("result"),
                "remark": self._body.get("remark"),
                "running_time": self._body.get("running_time"),
                "success_cases": self._body.get("success_cases"),
                "fail_cases": self._body.get("fail_cases"),
            }
