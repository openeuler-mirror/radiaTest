import json
import requests
from datetime import datetime

from flask import current_app
from celery import group
# from celery.canvas import GroupResult

from server.utils.db import Edit, Insert
from server.model.job import Job
from server.model.testcase import Suite
from server.model.task import TaskMilestone
from server.model.template import Template
from celeryservice.lib import TaskAuthHandler
from celeryservice.sub_tasks import run_case


# TODO 新增部分机器是已指定机器的场景
# TODO 新增指定机器作为master的场景
class RunJob(TaskAuthHandler):
    def __init__(self, body, promise, user, logger) -> None:
        self._body = body
        self.promise = promise
        super().__init__(user, logger)

    def _create_job(self):
        if self._body.get("id"):
            del self._body["id"]

        job_id = Insert(Job, self._body).insert_id(Job, "/job")

        if not job_id:
            raise RuntimeError(
                "Failed to create job:%s."
                % self.name
            )

        return Job.query.filter_by(id=job_id).first()


class RunSuite(RunJob):
    def run(self):
        self.promise.update_state(
            state="RUNNING",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            },
        )

        self._job = self._create_job()
        self._body.update(self._job.to_json())
        self._body.pop("milestone")

        suite = Suite.query.filter_by(
            id=self._body.get("suite_id")
        ).first()

        if not suite:
            raise RuntimeError(
                "test suite of id: {} does not exist, please check testcase repo.".format(
                    self._body.get("suite_id"))
            )

        suites_cases = [(suite.name, case.name) for case in suite.case]

        _task = run_case.delay(
            self.user,
            self._body,
            suite.machine_type,
            suite.machine_num,
            suite.add_network_interface,
            suite.add_disk,
            suites_cases,
        )

        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "group_tasks_result": _task.get(),
                "start_time": self.start_time,
                "running_time": self.running_time,
                **self._body,
            }
        )


class RunTemplate(RunJob):
    def __init__(self, body, promise, user, logger) -> None:
        super().__init__(body, promise, user, logger)

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
        })

        # for key in list(self._body.keys()):
        #     if not self._body.get(key):
        #         del self._body[key]
        # if not self._body.get("milestone_id"):
        #     self._body.update({"milestone_id": self._template.milestone_id})

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
                        for i in range(len(cases)-1, -1, -1):
                            if (
                                cases[i].machine_num == machine
                                and cases[i].add_network_interface == network
                                and cases[i].add_disk == disk
                            ):
                                _case = cases.pop(i)
                                cl.append([_case.suite.name, _case.name])

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
            self.promise.update_state(
                state="PREPARING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                },
            )

            self._job = self._create_job()
            self._body.update(self._job.to_json())
            self._body.pop("milestone")

            if self._job and self._body.get("taskmilestone_id"):
                resp = self._callback_task_job_init()
                if resp.status_code != 200:
                    self.logger.error(
                        "Cannot callback job_id to taskmilestone table: " + resp.error_mesg
                    )

            self._body.update({
                "total": len(self._template.cases),
                "success_cases": 0,
                "fail_cases": 0,
            })

            self.next_period()
            self.promise.update_state(
                state="CLASSIFYING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                    **self._body,
                },
            )

            classify_cases = self._sort()

            tasks = []
            for cases in classify_cases:
                tasks.append(
                    run_case.s(
                        self.user,
                        self._body,
                        cases.get("type"),
                        cases.get("machine"),
                        cases.get("network"),
                        cases.get("disk"),
                        cases.get("suites_cases"),
                    )
                )

            g_task = group(tasks).apply_async()

            self.next_period()
            self.promise.update_state(
                state="DONE",
                meta={
                    "group_task_id": g_task.id,
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                    **self._body,
                }
            )

        except RuntimeError as e:
            self.logger.error(str(e))

            self._body.update({
                "result": "fail",
                "remark": str(e),
                "end_time": datetime.now()
            })
            self.promise.update_state(
                state="BLOCK",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                    **self._body,
                },
            )

        finally:
            if self._body.get("taskmilestone_id"):
                self._callback_task_job_result()
