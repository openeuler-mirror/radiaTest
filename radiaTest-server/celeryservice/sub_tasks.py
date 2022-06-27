# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 
# @email   : 
# @Date    : 
# @License : Mulan PSL v2


#####################################

from datetime import datetime
import json
import requests
from flask import current_app
from celery import current_app as celery
from celery.utils.log import get_task_logger

from server.utils.db import Insert, Edit, collect_sql_error
from server.model.testcase import Suite, Case
from server.model.framework import GitRepo
from server.schema.testcase import SuiteBase, SuiteUpdate, CaseUpdateSchemaWithSuiteId, CaseBaseSchemaWithSuiteId
from server.utils.response_util import RET


logger = get_task_logger('manage')


@celery.task
@collect_sql_error
def update_case(case_data):
    same_case = Case.query.filter_by(name=case_data.get("name")).first()
    if not same_case:
        logger.info("create {}".format(case_data["name"]))
        _data = CaseBaseSchemaWithSuiteId(**case_data).__dict__
        _repo = GitRepo.query.filter_by(id=case_data.get("git_repo_id")).first()
        _data["permission_type"] = "group"
        _data["group_id"] = _repo.group_id
        _data["org_id"] = _repo.org_id
        _ = Insert(Case, _data).insert_id(Case, "/case")
    else:
        logger.info("update {}".format(case_data["name"]))
        case_data.update({"id": same_case.id})
        _data = CaseUpdateSchemaWithSuiteId(**case_data).__dict__
        _data["permission_type"] = "group"
        _data["group_id"] = _repo.group_id
        _data["org_id"] = _repo.org_id
        _ = Edit(Case, _data).single(Case, "/case")



@celery.task
def update_suite(suite_data, cases_data):
    logger.warn(suite_data["name"])

    suite_id = None
    same_suite = Suite.query.filter_by(name=suite_data.get("name")).first()
    _repo = GitRepo.query.filter_by(id=suite_data.get("git_repo_id")).first()

    if not same_suite:
        _data = SuiteBase(**suite_data).__dict__

        _data["permission_type"] = "group"
        _data["group_id"] = _repo.group_id
        _data["org_id"] = _repo.org_id
        suite_id = Insert(
            Suite,
            _data
        ).insert_id(Suite, "/suite")
    else:
        suite_data.update({"id": same_suite.id})
        _data = SuiteUpdate(**suite_data).__dict__
        _data["permission_type"] = "group"
        _data["group_id"] = _repo.group_id
        _data["org_id"] = _repo.org_id
        _ = Edit(Suite, _data).single(Suite, "/suite")

        suite_id = same_suite.id

    for case_data in cases_data:
        case_data.update({"suite_id": suite_id})
        case_data.update({"git_repo_id": _repo.id})
        _ = update_case.delay(case_data)
