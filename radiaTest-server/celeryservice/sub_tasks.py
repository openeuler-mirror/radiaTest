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
