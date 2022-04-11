from copy import deepcopy
from datetime import datetime

from flask import current_app
from celery import chord

from messenger.utils.requests_util import query_request, create_request, update_request
from messenger.utils.response_util import RET
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
        return query_request(
            "/api/v1/accessable_machines",
            {
                "machine_group_id": self._body.get("machine_group_id"),
                "machine_purpose": "run_job",
                "machine_type": "physical",
                "frame": self._body.get("frame"),
                "get_object": False,
            },
            self.user.get("auth")
        )

    def _create_job(self, multiple: bool, is_suite_job: bool):
        if self._body.get("id"):
            del self._body["id"]
        
        self._body.update({
            "multiple": multiple,
            "is_suite_job": is_suite_job,
        })

        job = create_request(
            "/api/v1/job",
            self._body,
            self.user.get("auth")
        )

        if not job:
            raise RuntimeError(
                "Failed to create job:%s."
                % self._body.get("name")
            )

        self._body.update(job)
        self._body.pop("milestone")
    
    def _update_job(self, **kwargs):
        self.next_period()
        self._body.update({
            "running_time": self.running_time,
            **kwargs,
        })
        
        update_body = deepcopy(self._body)
        update_body.pop("id")
        if isinstance(update_body.get("master"), list):
            update_body.update(
                {
                    "master": ','.join(update_body.get("master"))
                }
            )

        update_request(
            "/api/v1/job/{}".format(
                self._body.get("id")
            ),
            update_body,
            self.user.get("auth")
        )


class RunSuite(RunJob):
    def run(self):
        self._create_job(multiple=False, is_suite_job=True)

        try:
            suite = query_request(
                "/api/v1/suite/{}".format(
                    self._body.get("suite_id")
                ),
                None,
                self.user.get("auth")
            )

            if not suite:
                raise RuntimeError(
                    "test suite of id: {} does not exist, please check testcase repo.".format(
                        self._body.get("suite_id"))
                )

            cases = query_request(
                "/api/v1/case/preciseget",
                {
                    "suite_id": suite.get("id"),
                    "automatic": 1,
                    "usabled": 1,
                },
                self.user.get("auth")
            )

            if not cases:
                raise RuntimeError(
                    "the automatical and usabled testcases of suite {} do not exits".format(suite.get("name"))
                )

            env_params = {
                "machine_type": suite.get("machine_type"),
                "machine_num": suite.get("machine_num"),
                "add_network_interface": suite.get("add_network_interface"),
                "add_disk": suite.get("add_disk"),
            }

            suites_cases = [
                (
                    suite.get("name"), 
                    case.get("name")
                ) for case in cases
            ]
            
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
        
        self._template = query_request(
            "/api/v1/template/{}".format(
                self._body.get("template_id")
            ),
            None,
            self.user.get("auth")
        )

        if not self._template:
            raise RuntimeError(
                "template with id {} is not exist".format(
                    self._body.get("template_id")
                )
            )

        _git_repo = self._template.get("git_repo")
        
        self._body.update({
            "milestone_id": self._template.get("milestone_id"),
            "git_repo_id": _git_repo.get("id") if _git_repo else None,
            "total": len(self._template.get("cases")),
            "success_cases": 0,
            "fail_cases": 0,
        })

    def _sort(self):
        cases = self._template.get("cases")

        if not cases:
            raise RuntimeError(
                "template {} has no relative cases.".format(
                    self._template.get("name")
                )
            )

        machine_type = set()
        machine_num = set()
        add_network = set()
        add_disk = set()
        for case in cases:
            machine_type.add(case.get("machine_type"))
            machine_num.add(case.get("machine_num"))
            add_network.add(case.get("add_network_interface"))
            add_disk.add(case.get("add_disk"))

        classify_cases = []
        for m_type in machine_type:
            for machine in machine_num:
                for network in add_network:
                    for disk in add_disk:
                        cs = {}
                        cl = []
                        for case in cases:
                            if (
                                case["machine_num"] == machine
                                and case["add_network_interface"] == network
                                and case["add_disk"] == disk
                            ):
                                cl.append([case["suite"], case["name"]])

                        if cl:
                            cs["type"] = m_type
                            cs["machine"] = machine
                            cs["network"] = network
                            cs["disk"] = disk
                            cs["suites_cases"] = cl
                            classify_cases.append(cs)

        return classify_cases

    def _callback_task_job_init(self):
        return update_request(
            "/api/v1/task/milestones/{}".format(
                self._body.get("taskmilestone_id")
            ),
            {
                "job_id": self._body.get("id"),
            },
            self.user.get("auth")
        )

    def run(self):
        self._create_job(multiple=True, is_suite_job=False)

        try:
            if self._body.get("id") and self._body.get("taskmilestone_id"):
                resp = self._callback_task_job_init()
                if resp.get("error_code") != RET.OK:
                    self.logger.warn(
                        "cannot callback job_id to taskmilestone table: " + resp.get("error_mesg")
                    )

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
                    auth=self.user.get("auth"),
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
