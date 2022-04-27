from copy import deepcopy
from datetime import datetime
from celery import current_app as celery
from celery.utils.log import get_task_logger

from celeryservice import celeryconfig
from messenger.utils.requests_util import update_request, query_request, do_request
from messenger.utils.response_util import RET
from celeryservice.lib.job.case_handler import RunCaseHandler


logger = get_task_logger('manage')


@celery.task(bind=True)
def run_case(self, user, body, env_params, suites_cases, pmachine_pool):
    return RunCaseHandler(user, logger, self, body).work(
        env_params, suites_cases, pmachine_pool,
    )


def _callback_task_job_result(job_id, auth, taskmilestone_id, status):
        try:
            _resp = dict()
            _r = do_request(
                method="put",
                url="https://{}/api/v1/task/milestones/{}".format(
                    celeryconfig.server_addr,
                    taskmilestone_id
                ),
                body={
                    "job_id": job_id,
                    "result": status,
                },
                headers={
                    "content-type": "application/json;charset=utf-8",
                    "authorization": auth,
                },
                obj=_resp,
            )

            if _r == 0 and _resp.get("error_code") == RET.OK:
                logger.info(
                    "Task job has been call back => " + _resp.get("error_msg")
                )
            else:
                logger.error(
                    "Error in calling back to TaskMilestones => " + _resp.get(
                        "error_msg"
                    )
                )
        except (AttributeError, TypeError, RuntimeError, KeyError) as e:
            logger.error(
                "Error in calling back to TaskMilestones => " + str(e)
            )

@celery.task(bind=True)
def job_result_callback(self, results, auth, job_id=None, taskmilestone_id=None):
    try:
        job = query_request(
            "/api/v1/job/{}".format(
                job_id
            ),
            None,
            auth
        )
        
        if not job:
            raise RuntimeError("Job has already not existed")

        job["running_time"] = 0

        for result in results:
            if result.get("status") == "BLOCK":
                raise RuntimeError(
                    "one of subtask blocked: {}, because {}".format(
                        result.get("name"),
                        result.get("remark"),
                    )
                )

            job["success_cases"] += result.get("success_cases")
            job["fail_cases"] += result.get("fail_cases")
            job["running_time"] = max(
                job["running_time"], 
                result.get("running_time")
            )
            
        job["status"] = "DONE"
        job["end_time"] = datetime.now()

        if job["total"] == job["success_cases"]:
            job["result"] = "success"
        else:
            job["result"] = "fail"
        
    except RuntimeError as e:
        job["result"] = "fail"
        job["status"] = "BLOCK"
        job["remark"] = str(e)
    
    finally:
        status = job.get("status")

        _body = deepcopy(job)
        _body.pop("id")

        if isinstance(_body.get("master"), list):
            _body["master"] = ','.join(_body.get("master"))

        update_request(
            "/api/v1/job/{}".format(
                job_id,
            ),
            _body,
            auth
        )
        
        if taskmilestone_id is not None:
            _callback_task_job_result(job_id, auth, taskmilestone_id, status)

