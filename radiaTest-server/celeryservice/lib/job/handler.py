import json
from datetime import datetime

from flask import current_app
from sqlalchemy import or_, and_
from celery import chord

from server.utils.db import Edit, Insert
from server.utils.response_util import RET
from server.utils.permission_utils import PermissionItemsPool
from server.model.job import Job
from server.model.user import User
from server.model.testcase import Suite
from server.model.pmachine import Pmachine
from server.model.task import TaskMilestone
from server.model.template import Template
from celeryservice.lib import TaskAuthHandler
from celeryservice.sub_tasks import job_result_callback, run_case


class RunJob(TaskAuthHandler):
    def __init__(self, body, promise, user, logger) -> None:
        self._body = body
        self.promise = promise
        self.app_context= current_app.app_context()

        super().__init__(user, logger)

        self._body.update({
            "status": "PENDING",
            "start_time": self.start_time,
            "running_time": 0,
        })

    @property
    def pmachine_pool(self):
        user= User.query.filter_by(
            gitee_id=self.user.get("user_id")
        ).first()

        _pmachines = Pmachine.query.filter(
            Pmachine.frame==self._body.get("frame"),
            Pmachine.state=="occupied",
            Pmachine.locked==False,
            Pmachine.status=="on",
            or_(
                Pmachine.description==current_app.config.get("CI_PURPOSE"),
                and_(
                    Pmachine.occupier==user.gitee_name,
                    Pmachine.description!=current_app.config.get(
                        "CI_HOST"
                    )
                )
            ),
        ).all()

        return PermissionItemsPool(
            _pmachines,
            "pmachine",
            "GET",
            self.user.get("auth")
        ).allow_list

    def _create_job(self, multiple: bool):
        if self._body.get("id"):
            del self._body["id"]
        
        self._body.update({
            "multiple": multiple,
            "is_suite_job": True,
        })

        job_id = Insert(Job, self._body).insert_id(Job, "/job")

        if not job_id:
            raise RuntimeError(
                "Failed to create job:%s."
                % self.name
            )

        _job = Job.query.filter_by(id=job_id).first()

        self._body.update(_job.to_dict())
        self._body.pop("milestone")
    
    def _update_job(self, app_context=None, **kwargs):
        self.next_period()
        self._body.update({
            "running_time": self.running_time,
            **kwargs,
        })
        
        if app_context is not None:
            with app_context:
                job = Job.query.filter_by(id=self._body.get("id")).first()
                for key, value in self._body.items():
                    setattr(job, key, value)

                job.add_update(Job, "/job", True)
        else:
            job = Job.query.filter_by(id=self._body.get("id")).first()
            for key, value in self._body.items():
                setattr(job, key, value)
            
            job.add_update(Job, "/job", True)


class RunSuite(RunJob):
    def run(self):
        self._create_job(False)

        try:
            suite = Suite.query.filter_by(
                id=self._body.get("suite_id")
            ).first()

            if not suite:
                raise RuntimeError(
                    "test suite of id: {} does not exist, please check testcase repo.".format(
                        self._body.get("suite_id"))
                )

            env_params = {
                "machine_type": suite.machine_type,
                "machine_num": suite.machine_num,
                "add_network_interface": suite.add_network_interface,
                "add_disk": suite.add_disk,
            }

            suites_cases = [(suite.name, case.name) for case in suite.case]
            
            _task = run_case.delay(
                self.user,
                self._body,
                env_params,
                suites_cases,
                self.pmachine_pool,
            )

            self._update_job(tid = _task.task_id)
        
        except RuntimeError as e:
            self.logger.error(str(e))
            self._update_job(
                result="fail",
                remark=str(e),
                end_time=datetime.now(),
                status="BLOCK",
            )


class RunTemplate(RunJob):
    def __init__(self, body, promise, user, logger) -> None:
        super().__init__(body, promise, user, logger)

        self.progress = 0

        self._template = Template.query.filter_by(
            id=self._body.get("template_id")
        ).first()
        if not self._template:
            raise RuntimeError(
                "template with id {} is not exist".format(
                    self._body.get("template_id")
                )
            )
        self._body.update({
            "milestone_id": self._template.milestone_id,
            "git_repo_id": self._template.git_repo_id,
            "total": len(self._template.cases),
            "success_cases": 0,
            "fail_cases": 0,
        })

    def _sort(self):
        cases = self._template.cases
        if not cases:
            raise RuntimeError(
                "template {} has no relative cases.".format(self._template.name))

        machine_type = set()
        machine_num = set()
        add_network = set()
        add_disk = set()
        for case in cases:
            machine_type.add(case.machine_type)
            machine_num.add(case.machine_num)
            add_network.add(case.add_network_interface)
            add_disk.add(case.add_disk)

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
                            cs["suites_cases"] = cl
                            classify_cases.append(cs)

        return classify_cases

    def _callback_task_job_init(self):
        return Edit(
            TaskMilestone,
            {
                "id": self._body.get("taskmilestone_id"),
                "job_id": self._job.id
            }
        ).single()

    def run(self):
        self._create_job(True)

        try:
            if self._body.get("id") and self._body.get("taskmilestone_id"):
                resp = self._callback_task_job_init()
                try:
                    output = json.loads(resp.text)
                    if output.get("error_code") != RET.OK:
                        self.logger.error(
                            "Cannot callback job_id to taskmilestone table: " + resp.error_mesg
                        )
                except (AttributeError, TypeError, RuntimeError) as e:
                    self.logger.error(str(e))
                    raise RuntimeError(str(e)) from e

            self._update_job(
                status="CLASSIFYING",
            )

            classify_cases = self._sort()

            tasks = []
            for cases in classify_cases:
                env_params = {
                    "machine_type": cases.get("type"),
                    "machine_num": cases.get("machine"),
                    "add_network_interface": cases.get("network"),
                    "add_disk": cases.get("disk"),
                }

                tasks.append(
                    run_case.s(
                        self.user,
                        self._body,
                        env_params,
                        cases.get("suites_cases"),
                        self.pmachine_pool,
                    )
                )

            chord_task = chord(tasks)(
                job_result_callback.s(
                    job_id=self._body.get("id"),
                    taskmilestone_id=self._body.get("taskmilestone_id")
                )
            )

            self._update_job(
                status="RUNNING",
                tid=chord_task.task_id,
            )

        except RuntimeError as e:
            self.logger.error(str(e))
            self._update_job(
                result="fail",
                remark=str(e),
                end_time=datetime.now(),
                status="BLOCK",
            )
