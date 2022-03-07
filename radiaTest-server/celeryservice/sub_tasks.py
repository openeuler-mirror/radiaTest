from datetime import datetime
import json
import requests
from flask import current_app
from celery import current_app as celery
from celery.utils.log import get_task_logger

from server.utils.db import Insert, Edit, collect_sql_error
from server.model.testcase import Suite, Case
from server.model.job import Job
from server.schema.testcase import SuiteBase, SuiteUpdate, CaseUpdateSchemaWithSuiteId, CaseBaseSchemaWithSuiteId
from server.utils.response_util import RET
from celeryservice.lib.job.case_handler import RunCaseHandler


logger = get_task_logger('manage')


@celery.task
@collect_sql_error
def update_case(case_data):
    same_case = Case.query.filter_by(name=case_data.get("name")).first()

    if not same_case:
        logger.info("create {}".format(case_data["name"]))
        _ = Insert(Case, CaseBaseSchemaWithSuiteId(
            **case_data).__dict__).insert_id(Case, "/case")
    else:
        logger.info("update {}".format(case_data["name"]))
        case_data.update({"id": same_case.id})
        _ = Edit(Case, CaseUpdateSchemaWithSuiteId(
            **case_data).__dict__).single(Case, "/case")



@celery.task
def update_suite(suite_data, cases_data):
    logger.warn(suite_data["name"])

    suite_id = None
    same_suite = Suite.query.filter_by(name=suite_data.get("name")).first()

    if not same_suite:
        suite_id = Insert(
            Suite,
            SuiteBase(**suite_data).__dict__
        ).insert_id(Suite, "/suite")
    else:
        suite_data.update({"id": same_suite.id})
        _ = Edit(
            Suite,
            SuiteUpdate(**suite_data).__dict__
        ).single(Suite, "/suite")

        suite_id = same_suite.id

    for case_data in cases_data:
        case_data.update({"suite_id": suite_id})
        _ = update_case.delay(case_data)


@celery.task(bind=True)
def run_case(self, user, body, env_params, suites_cases, pmachine_pool):
    return RunCaseHandler(user, logger, self, body).work(
        env_params, suites_cases, pmachine_pool,
    )


def _callback_task_job_result(job_id, taskmilestone_id, status):
        try:
            resp = requests.put(
                url="{}://{}:{}/api/v1/task/milestones/{}".format(
                    current_app.config.get("PROTOCOL"),
                    current_app.config.get("SERVER_IP"),
                    current_app.config.get("SERVER_PORT"),
                    taskmilestone_id
                ),
                data=json.dumps({
                    "job_id": job_id,
                    "result": status,
                }),
                headers=current_app.config.get("HEADERS")
            )
            resp.encoding = resp.apparent_encoding

            output = json.loads(resp.text)

            if output.get("error_code") == RET.OK:
                logger.info(
                    "Task job has been call back => " + output.get("error_msg")
                )
            else:
                logger.error(
                    "Error in calling back to TaskMilestones => " + output.get(
                        "error_msg"
                    )
                )
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Error in calling back to TaskMilestones => " + str(e)
            )

@celery.task(bind=True)
def job_result_callback(self, results, job_id=None, taskmilestone_id=None):
    try:
        job = Job.query.filter_by(id=job_id).first()
        if not job:
            raise RuntimeError("Job has already not existed")

        job.running_time = 0

        for result in results:
            if result.get("status") == "BLOCK":
                raise RuntimeError(
                    "one of subtask blocked: {}, because {}".format(
                        result.get("name"),
                        result.get("remark"),
                    )
                )

            job.success_cases += result.get("success_cases")
            job.fail_cases += result.get("fail_cases")
            job.running_time = max(job.running_time, result.get("running_time"))
            
        job.status = "DONE"
        job.end_time = datetime.now()

        if job.total == job.success_cases:
            job.result = "success"
        else:
            job.result = "fail"
        
    except RuntimeError as e:
        job.result = "fail"
        job.status = "BLOCK"
        job.remark = str(e)
    
    finally:
        status = job.status

        job.add_update(Job, "/job", True)

        if taskmilestone_id is not None:
            _callback_task_job_result(job_id, taskmilestone_id, status)

