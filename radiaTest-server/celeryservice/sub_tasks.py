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
from server.model.testcase import Suite, Case, CaseNode
from server.model.framework import GitRepo
from server.schema.testcase import SuiteBase, SuiteUpdate, CaseBaseSchemaWithSuiteId
from server.model.qualityboard import SameRpmCompare, RpmCompare


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


@celery.task
def update_daily_compare_result(daily_name, comparer_round_name, compare_results, repeat_list, file_path):
    import xlwt

    cnt = 1
    wb = xlwt.Workbook()
    ws = wb.add_sheet("软件范围")
    ws.write(0, 0, daily_name)
    ws.write(0, 1, comparer_round_name)
    ws.write(0, 2, "arch")
    ws.write(0, 3, "compare result")
    
    for result in compare_results:
        ws.write(cnt, 0, result.get("rpm_list_1"))
        ws.write(cnt, 1, result.get("rpm_list_2"))
        ws.write(cnt, 2, result.get("arch"))
        ws.write(cnt, 3, result.get("compare_result"))
        cnt += 1

    ws = wb.add_sheet(f"{daily_name}多版本rpm")
    ws.write(0, 0, "rpm name")
    ws.write(0, 1, "arch")
    ws.write(0, 2, "release")
    ws.write(0, 3, "version")
    cnt = 1
    for rpm in repeat_list:
        ws.write(cnt, 0, rpm.get("rpm_file_name"))
        ws.write(cnt, 1, rpm.get("arch"))
        ws.write(cnt, 2, rpm.get("release"))
        ws.write(cnt, 3, rpm.get("version"))
        cnt += 1

    wb.save(file_path)


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


@celery.task
@collect_sql_error
def create_case_node_multi_select(body):
    from server import db

    def insert_case_node(body):
        _casenode = CaseNode(
            title=body.get("title"),
            type=body.get("type"),
            is_root=False,
            in_set=body.get("in_set"),
            group_id=body.get("group_id"),
            org_id=body.get("org_id"),
            creator_id=body.get("creator_id"),
            case_id=body.get("case_id") if body.get("case_id") else None,
            suite_id=body.get("suite_id") if body.get("suite_id") else None,
            baseline_id=body.get("baseline_id") if body.get("baseline_id") else None,
            permission_type=body.get("permission_type")
        )
        db.session.add(_casenode)
        db.session.commit()
        parent = CaseNode.query.filter_by(id=body.get("parent_id")).first()
        _casenode.parent.append(parent)
        _casenode.add_update()

    if body.get("type") == "case":
        case_ids = body.get("case_ids")[:]
        body.pop("case_ids")
        for _id in case_ids:
            _case = Case.query.get(_id)
            if _case:
                body["case_id"] = _id
                body["title"] = _case.name
                insert_case_node(body)
    elif body.get("type") == "suite":
        suite_ids = body.get("suite_ids")[:]
        body.pop("suite_ids")
        for _id in suite_ids:
            _suite = Suite.query.get(_id)
            if _suite:
                body["suite_id"] = _id
                body["title"] = _suite.name
                insert_case_node(body)
        