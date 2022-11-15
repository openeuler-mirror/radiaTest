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
from celery import current_app as celery
from celery.utils.log import get_task_logger

from server.utils.db import Insert, Edit, collect_sql_error
from server.model.testcase import Suite, Case
from server.model.framework import GitRepo
from server.schema.testcase import SuiteBase, SuiteUpdate, CaseUpdateSchemaWithSuiteId, CaseBaseSchemaWithSuiteId
from server.model.qualityboard import SameRpmCompare# , RpmCompare


logger = get_task_logger('manage')


@celery.task
def update_case(case_data):
    same_case = Case.query.filter_by(name=case_data.get("name")).first()
    if not same_case:
        logger.info("create {}".format(case_data["name"]))
        _data = CaseBaseSchemaWithSuiteId(**case_data).__dict__
        _ = Insert(Case, _data).insert_id(Case, "/case")
    else:
        logger.info("update {}".format(case_data["name"]))
        _data = CaseBaseSchemaWithSuiteId(**case_data).__dict__
        _data.update({"id": same_case.id})
        _ = Edit(Case, _data).single(Case, "/case")


@celery.task
def update_suite(suite_data, cases_data):
    suite_id = None
    same_suite = Suite.query.filter_by(name=suite_data.get("name")).first()
    _repo = GitRepo.query.filter_by(id=suite_data.get("git_repo_id")).first()

    if not same_suite:
        _data = SuiteBase(**suite_data).__dict__
        _data.update({
            "permission_type": _repo.permission_type,
            "group_id": _repo.group_id,
            "org_id": _repo.org_id,
            "creator_id": _repo.creator_id
        })
        suite_id = Insert(
            Suite,
            _data
        ).insert_id(Suite, "/suite")
    else:
        suite_data.update({"id": same_suite.id})
        _data = SuiteUpdate(**suite_data).__dict__
        _data.update({
            "permission_type": _repo.permission_type,
            "group_id": _repo.group_id,
            "org_id": _repo.org_id,
            "creator_id": _repo.creator_id
        })
        _ = Edit(Suite, _data).single(Suite, "/suite")

        suite_id = same_suite.id

    for case_data in cases_data:
        case_data.update({
            "suite_id": suite_id,
            "git_repo_id": _repo.id,
            "permission_type": _repo.permission_type,
            "group_id": _repo.group_id,
            "org_id": _repo.org_id,
            "creator_id": _repo.creator_id
        })
        _ = update_case.delay(case_data)


@celery.task
def update_compare_result(round_group_id: int, results, repo_path):
    pass
    '''
    for result in results:
        if not round_group_id:
            raise ValueError("lack of param round_group_id")

        rpm_compare = RpmCompare.query.filter_by(
            rpm_comparee=result.get("rpm_list_1"),
            rpm_comparer=result.get("rpm_list_2"),
            round_group_id=round_group_id
        ).first()
        if not rpm_compare:
            _ = Insert(
                RpmCompare, 
                {
                    "repo_path": repo_path,
                    "arch": result.get("arch"),
                    "rpm_comparee": result.get("rpm_list_1"),
                    "rpm_comparer": result.get("rpm_list_2"),
                    "compare_result": result.get("compare_result"),
                    "round_group_id": round_group_id,
                }
            ).single()
        else:
            _ = Edit(
                RpmCompare,
                {   
                    "id": rpm_compare.id,
                    "compare_result": result.get("compare_result"),
                }
            ).single()
    '''

@celery.task
def update_samerpm_compare_result(round_id: int, results, repo_path):
    for result in results:
        rpm_compare = SameRpmCompare.query.filter_by(
            rpm_x86=result.get("rpm_x86"),
            rpm_arm=result.get("rpm_arm"),
            round_id=round_id
        ).first()
        if not rpm_compare:
            _ = Insert(
                SameRpmCompare, 
                {
                    "repo_path": repo_path,
                    "rpm_name": result.get("rpm_name"),
                    "rpm_x86": result.get("rpm_x86"),
                    "rpm_arm": result.get("rpm_arm"),
                    "compare_result": result.get("compare_result"),
                    "round_id": round_id,
                }
            ).single()
        else:
            _ = Edit(
                SameRpmCompare,
                {   
                    "id": rpm_compare.id,
                    "compare_result": result.get("compare_result"),
                }
            ).single()