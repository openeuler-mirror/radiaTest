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

import json
from celery import current_app as celery
import sqlalchemy
from server.utils.response_util import RET
from server.utils.db import Insert
from server.model.milestone import Milestone, IssueSolvedRate
from server.model.organization import Organization
from server.model.product import Product
from server.model.qualityboard import Round
from server.apps.milestone.handler import GiteeV8BaseIssueHandler
from celeryservice.lib import TaskHandlerBase


class UpdateIssueRateData:
    def __init__(self, products):
        self.products = products
        self.issue_v8 = GiteeV8BaseIssueHandler(
            org_id=products.get("org_id")
        )
        self.bug_issue_type_id = self.issue_v8.get_bug_issue_type_id("缺陷")

        self.all_state_ids = self.issue_v8.get_state_ids_inversion(
            set(["已挂起", "已取消", "已拒绝"])
        )
        self.serious_state_ids = self.issue_v8.get_state_ids(
            set(["已完成", "已验收", "已挂起", "已取消", "已拒绝"])
        )
        self.current_resolved_state_ids = self.issue_v8.get_state_ids(
            set(["已完成", "已验收"])
        )
        self.left_state_ids = self.issue_v8.get_state_ids(
            set(["已挂起"])
        )
        self.invalid_state_ids = self.issue_v8.get_state_ids(
            set(["已取消", "已拒绝"])
        )
        self.issue_query_param = {
            "milestone_id": "",
            "issue_type_id": self.bug_issue_type_id,
        }
        self.all_issues_cnt, self.all_issues = self.get_all_issues_by_product()

        self.param = {
            "serious_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": 4,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": 4,
                    "issue_state_ids": self.serious_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "serious_resolved_rate": "",
                    "serious_resolved_passed": None,
                },
                "m_fields": {
                    "serious_resolved_rate": "",
                    "serious_resolved_passed": None,
                }
            },
            "main_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": 3,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": 3,
                    "issue_state_ids": self.serious_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "main_resolved_rate": "",
                    "main_resolved_passed": None,
                },
                "m_fields": {
                    "main_resolved_rate": "",
                    "main_resolved_passed": None,
                },
            },
            "serious_main_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": "3,4",
                    "issue_type_id": self.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": "3,4",
                    "issue_state_ids": self.serious_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "serious_main_resolved_cnt": "",
                    "serious_main_all_cnt": "",
                    "serious_main_resolved_rate": "",
                    "serious_main_resolved_passed": None,
                },
                "m_fields": {
                    "serious_main_resolved_rate": "",
                    "serious_main_resolved_cnt": "",
                    "serious_main_all_cnt": "",
                    "serious_main_resolved_passed": None,
                }
            },
            "current_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "issue_state_ids": self.all_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "issue_state_ids": self.current_resolved_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "current_resolved_cnt": "",
                    "current_all_cnt": "",
                    "current_resolved_rate": "",
                    "current_resolved_passed": None,
                },
                "m_fields": {
                    "current_resolved_rate": "",
                    "current_resolved_cnt": "",
                    "current_all_cnt": "",
                    "current_resolved_passed": None,
                }
            },
            "left_issues_cnt": {
                "all": {
                    "milestone_id": "",
                    "issue_state_ids": self.left_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "left_issues_cnt": "",
                    "left_issues_passed": None,
                },
                "m_fields": {
                    "left_issues_cnt": "",
                    "left_issues_passed": None,
                }
            },
            "invalid_issues_cnt": {
                "all": {
                    "milestone_id": "",
                    "issue_state_ids": self.invalid_state_ids,
                    "issue_type_id": self.bug_issue_type_id,
                },
                "p_fields": {
                    "invalid_issues_cnt": "",
                    "invalid_issues_passed": None,
                },
                "m_fields": {
                    "invalid_issues_cnt": "",
                    "invalid_issues_passed": None,
                }
            },

        }

    def get_all_issues_by_product(self):
        milestones = Milestone.query.filter_by(
            product_id=self.products.get("product_id"), is_sync=True
        ).all()
        if not milestones:
            return 0, []
        param = self.issue_query_param
 
        milestone_ids = ""
        for _milestone in milestones:
            milestone_ids = ",".join(
                [milestone_ids, str(_milestone.gitee_milestone_id)]
            )

        param.update({"milestone_id": milestone_ids})
        page = 1
        per_page = 100
        all_issues = []
        param.update({
            'per_page': per_page,
            'page': page,
        })
        total, per_issues = self.issue_v8.get_all_issues(param)
        all_issues = all_issues + per_issues[:]
        while len(all_issues) < total:
            page += 1
            param.update({
                'page': page,
            })
            _, per_issues = self.issue_v8.get_all_issues(param)
            all_issues = all_issues + per_issues[:]

        return total, all_issues
    
    def update_issue_resolved_rate_product(self):
        from server.apps.qualityboard.handlers import QualityResultCompareHandler
        serious_main_cnt = 0
        serious_main_resolved_cnt = 0
        serious_main_resolved_rate = "100%"
        current_cnt = 0
        current_resolved_cnt = 0
        current_resolved_rate = "100%"
         
        for issue in self.all_issues:
            if issue.get("priority") in [3, 4]:
                serious_main_cnt += 1
                if str(issue.get("issue_state_id")) in self.serious_state_ids:
                    serious_main_resolved_cnt += 1
            if str(issue.get("issue_state_id")) in self.all_state_ids:
                    current_cnt += 1
            if str(issue.get("issue_state_id")) in self.current_resolved_state_ids:
                    current_resolved_cnt += 1
                    
        if serious_main_cnt == 0:
            serious_main_resolved_rate = "100%"
        else:
            solved_rate = serious_main_resolved_cnt / serious_main_cnt
            serious_main_resolved_rate = "%.f%%" % (solved_rate * 100)

        if current_cnt == 0:
            current_resolved_rate = "100%"
        else:
            solved_rate = current_resolved_cnt / current_cnt
            current_resolved_rate = "%.f%%" % (solved_rate * 100)

        qrsh = QualityResultCompareHandler("product", self.products.get("product_id"))
        serious_main_resolved_passed = qrsh.compare_issue_rate("serious_main_resolved_rate", serious_main_resolved_rate)
        current_resolved_rate_passed = qrsh.compare_issue_rate("current_resolved_rate", current_resolved_rate)

        issue_resolved_rate_dict = {
            "serious_main_resolved_cnt": serious_main_resolved_cnt,
            "serious_main_all_cnt": serious_main_cnt,
            "serious_main_resolved_rate": serious_main_resolved_rate,
            "serious_main_resolved_passed": serious_main_resolved_passed,
            "current_resolved_cnt": current_resolved_cnt,
            "current_all_cnt": current_cnt,
            "current_resolved_rate": current_resolved_rate,
            "current_resolved_passed": current_resolved_rate_passed,
        }

        product = Product.query.get(self.products.get("product_id"))
        for key, value in issue_resolved_rate_dict.items():
            if value is not None:
                setattr(product, key, value)
        product.add_update()

    def update_issue_resolved_rate_round(self, round_id):
        milestones = Milestone.query.filter_by(round_id=round_id, is_sync=True).all()
        if not milestones:
            return
        milestone_ids = []
        for m in milestones:
            milestone_ids.append(m.gitee_milestone_id)
        self.update_issue_resolved_rate_milestone(milestone_ids, rate_type="round", round_id=round_id)

    def update_issue_resolved_rate_milestone(self, milestone_ids: list, rate_type="milestone", round_id=None):
        from server.apps.qualityboard.handlers import QualityResultCompareHandler
        serious_cnt = 0
        serious_resolved_cnt = 0
        serious_resolved_rate = "100%"
        serious_resolved_passed = None
        main_cnt = 0
        main_resolved_cnt = 0
        main_resolved_rate = "100%"
        main_resolved_passed = None
        serious_main_cnt = 0
        serious_main_resolved_cnt = 0
        serious_main_resolved_rate = "100%"
        serious_main_resolved_passed = None
        current_cnt = 0
        current_resolved_cnt = 0
        current_resolved_rate = "100%"
        current_resolved_rate_passed = None
        left_issues_cnt = 0
        left_issues_passed = None
        invalid_issues_cnt = 0
        invalid_issues_passed = None
        for issue in self.all_issues:
            if issue.get("milestone").get("id") in milestone_ids:
                if issue.get("priority") == 3:
                    main_cnt += 1
                    serious_main_cnt += 1
                    if str(issue.get("issue_state_id")) in self.serious_state_ids:
                        main_resolved_cnt += 1
                        serious_main_resolved_cnt += 1
                if issue.get("priority") == 4:
                    serious_cnt += 1
                    serious_main_cnt += 1
                    if str(issue.get("issue_state_id")) in self.serious_state_ids:
                        serious_resolved_cnt += 1
                        serious_main_resolved_cnt += 1
                if str(issue.get("issue_state_id")) in self.all_state_ids:
                        current_cnt += 1
                if str(issue.get("issue_state_id")) in self.current_resolved_state_ids:
                        current_resolved_cnt += 1
                if str(issue.get("issue_state_id")) in self.left_state_ids:
                        left_issues_cnt += 1
                if str(issue.get("issue_state_id")) in self.invalid_state_ids:
                        invalid_issues_cnt += 1
 
        if serious_main_cnt == 0:
            serious_main_resolved_rate = "100%"
        else:
            solved_rate = serious_main_resolved_cnt / serious_main_cnt
            serious_main_resolved_rate = "%.f%%" % (solved_rate * 100)
        if main_cnt == 0:
            main_resolved_rate = "100%"
        else:
            solved_rate = main_resolved_cnt / main_cnt
            main_resolved_rate = "%.f%%" % (solved_rate * 100)
        if serious_cnt == 0:
            serious_resolved_rate = "100%"
        else:
            solved_rate = serious_resolved_cnt / serious_cnt
            serious_resolved_rate = "%.f%%" % (solved_rate * 100)

        if current_cnt == 0:
            current_resolved_rate = "100%"
        else:
            solved_rate = current_resolved_cnt / current_cnt
            current_resolved_rate = "%.f%%" % (solved_rate * 100)

        qrsh = QualityResultCompareHandler("product", self.products.get("product_id"))
        serious_main_resolved_passed = qrsh.compare_issue_rate("serious_main_resolved_rate", serious_main_resolved_rate)
        main_resolved_passed = qrsh.compare_issue_rate("main_resolved_rate", main_resolved_rate)
        serious_resolved_passed = qrsh.compare_issue_rate("serious_resolved_rate", serious_resolved_rate)
        current_resolved_rate_passed = qrsh.compare_issue_rate("current_resolved_rate", current_resolved_rate)
        left_issues_passed = qrsh.compare_issue_rate("left_issues_cnt", left_issues_cnt)
        invalid_issues_passed = qrsh.compare_issue_rate("invalid_issues_cnt", invalid_issues_cnt)

        issue_resolved_rate_dict = {
            "serious_main_resolved_cnt": serious_main_resolved_cnt,
            "serious_main_all_cnt": serious_main_cnt,
            "serious_main_resolved_rate": serious_main_resolved_rate,
            "serious_main_resolved_passed": serious_main_resolved_passed,
            "serious_resolved_rate": serious_resolved_rate,
            "serious_resolved_passed": serious_resolved_passed,
            "main_resolved_rate": main_resolved_rate,
            "main_resolved_passed": main_resolved_passed,
            "current_resolved_cnt": current_resolved_cnt,
            "current_all_cnt": current_cnt,
            "current_resolved_rate": current_resolved_rate,
            "current_resolved_passed": current_resolved_rate_passed,
            "left_issues_cnt": left_issues_cnt,
            "left_issues_passed": left_issues_passed,
            "invalid_issues_cnt": invalid_issues_cnt,
            "invalid_issues_passed": invalid_issues_passed
        }

        if rate_type == "round":
            issue_rate = IssueSolvedRate.query.filter_by(
                round_id=round_id, type="round").first()
        else:
            issue_rate = IssueSolvedRate.query.filter_by(
                gitee_milestone_id=milestone_ids[0]).first()
        if issue_rate:
            for key, value in issue_resolved_rate_dict.items():
                if value is not None:
                    setattr(issue_rate, key, value)
            issue_rate.add_update()

    def update_product_issue_resolved_rate(self, field: str):
        from server.apps.qualityboard.handlers import QualityResultCompareHandler
        milestones = Milestone.query.filter_by(
            product_id=self.products.get("product_id"), is_sync=True
        ).all()
        if not milestones:
            return
        param1 = self.param.get(field).get("all")
        if not param1:
            return
        issue_resolved_rate_dict = dict()
        milestone_ids = ""
        for _milestone in milestones:
            milestone_ids = ",".join(
                [milestone_ids, str(_milestone.gitee_milestone_id)]
            )

        param1.update({"milestone_id": milestone_ids})
        param2 = self.param.get(field).get("part")
        if param2:
            param2.update({"milestone_id": milestone_ids})

        resolved_cnt, all_cnt, resolved_rate = self.issue_v8.get_issue_cnt_rate(
            param1, param2
        )
        if all_cnt is None:
            return
        if resolved_cnt is None and param2 is not None:
            return
        field_val = all_cnt
        if "rate" in field:
            field_val = resolved_rate
        passed = None
        if field_val is not None:
            qrsh = QualityResultCompareHandler("product", self.products.get("product_id"))
            passed = qrsh.compare_issue_rate(field, field_val)

        _issuerate_dict = self.param.get(field).get("p_fields")
        for k in _issuerate_dict.keys():
            if "resolved_rate" in k:
                issue_resolved_rate_dict.update({k: resolved_rate})
            if "passed" in k:
                issue_resolved_rate_dict.update({k: passed})
            if "resolved_cnt" in k:
                issue_resolved_rate_dict.update({k: resolved_cnt})
            if "all_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})
            if "issues_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})

        product = Product.query.get(self.products.get("product_id"))
        for key, value in issue_resolved_rate_dict.items():
            if value is not None:
                setattr(product, key, value)
        product.add_update()

    def update_milestone_issue_resolved_rate(self, gitee_milestone_id, field: str):
        from server.apps.qualityboard.handlers import QualityResultCompareHandler
        param1 = self.param.get(field).get("all")
        if not param1:
            return
        param1.update({"milestone_id": gitee_milestone_id})
        param2 = self.param.get(field).get("part")
        if param2:
            param2.update({"milestone_id": gitee_milestone_id})
        resolved_cnt, all_cnt, resolved_rate = self.issue_v8.get_issue_cnt_rate(
            param1, param2
        )
        if all_cnt is None:
            return
        if resolved_cnt is None and param2 is not None:
            return
        field_val = all_cnt
        if "rate" in field:
            field_val = resolved_rate

        _m = Milestone.query.filter_by(
            gitee_milestone_id=gitee_milestone_id).first()
        passed = None
        if field_val is not None:
            qrsh = QualityResultCompareHandler("milestone", _m.id)
            passed = qrsh.compare_issue_rate(field, field_val)
        issue_resolved_rate_dict = dict()
        
        issue_resolved_rate_dict.update(
            {
                "milestone_id": _m.id,
                "gitee_milestone_id": gitee_milestone_id,
            }
        )
        _issuerate_dict = self.param.get(field).get("m_fields")
        for k in _issuerate_dict.keys():
            if "resolved_rate" in k:
                issue_resolved_rate_dict.update({k: resolved_rate})
            if "resolved_cnt" in k:
                issue_resolved_rate_dict.update({k: resolved_cnt})
            if "all_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})
            if "issues_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})
            if "passed" in k:
                issue_resolved_rate_dict.update({k: passed})

        issue_rate = IssueSolvedRate.query.filter_by(
            gitee_milestone_id=gitee_milestone_id).first()
        if issue_rate:
            for key, value in issue_resolved_rate_dict.items():
                if value is not None:
                    setattr(issue_rate, key, value)
            issue_rate.add_update()

    def update_round_issue_resolved_rate(self, round_id, field: str):
        from server.apps.qualityboard.handlers import QualityResultCompareHandler
        param1 = self.param.get(field).get("all")
        if not param1:
            return
        milestones = Milestone.query.filter_by(round_id=round_id, is_sync=True).all()
        if not milestones:
            return
        milestone_ids = ""
        for m in milestones:
            milestone_ids += f"{m.gitee_milestone_id},"
        milestone_ids = milestone_ids[:-1]
            
        param1.update({"milestone_id": milestone_ids})
        param2 = self.param.get(field).get("part")
        if param2:
            param2.update({"milestone_id": milestone_ids})
        resolved_cnt, all_cnt, resolved_rate = self.issue_v8.get_issue_cnt_rate(
            param1, param2
        )
        if all_cnt is None:
            return
        if resolved_cnt is None and param2 is not None:
            return
        field_val = all_cnt
        if "rate" in field:
            field_val = resolved_rate

        passed = None
        if field_val is not None:
            qrsh = QualityResultCompareHandler("round", round_id)
            passed = qrsh.compare_issue_rate(field, field_val)
        issue_resolved_rate_dict = dict()
        _issuerate_dict = self.param.get(field).get("m_fields")
        for k in _issuerate_dict.keys():
            if "resolved_rate" in k:
                issue_resolved_rate_dict.update({k: resolved_rate})
            if "resolved_cnt" in k:
                issue_resolved_rate_dict.update({k: resolved_cnt})
            if "all_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})
            if "issues_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})
            if "passed" in k:
                issue_resolved_rate_dict.update({k: passed})

        issue_rate = IssueSolvedRate.query.filter_by(
            round_id=round_id, type="round").first()
        if issue_rate:
            for key, value in issue_resolved_rate_dict.items():
                if value is not None:
                    setattr(issue_rate, key, value)
            issue_rate.add_update()


@celery.task
def update_field_issue_rate(obj_type: str, products: dict, field: str, obj_id=None):
    _uird = UpdateIssueRateData(products)
    if obj_type == "product":
        _uird.update_product_issue_resolved_rate(field)
    elif obj_type == "round":
        _uird.update_round_issue_resolved_rate(obj_id, field)
    elif obj_type == "milestone":
        _uird.update_milestone_issue_resolved_rate(obj_id, field)


class UpdateIssueRate(TaskHandlerBase):
    @staticmethod
    def update_product_issue_resolved_rate(products: dict):
        fields = ["serious_main_resolved_rate", "current_resolved_rate"]
        for _f in fields:
            update_field_issue_rate.delay(
                "product",
                products,
                _f
            )

    @staticmethod
    def update_round_issue_resolved_rate(products: dict, round_id):
        fields = ["serious_resolved_rate", "main_resolved_rate", "serious_main_resolved_rate",
                  "current_resolved_rate", "left_issues_cnt", "invalid_issues_cnt"]
        for _f in fields:
            update_field_issue_rate.delay(
                "round",
                products,
                _f,
                round_id,
            )

    @staticmethod
    def update_milestone_issue_resolved_rate(products: dict, gitee_milestone_id):
        fields = ["serious_resolved_rate", "main_resolved_rate", "serious_main_resolved_rate",
                  "current_resolved_rate", "left_issues_cnt", "invalid_issues_cnt"]
        for _f in fields:
            update_field_issue_rate.delay(
                "milestone",
                products,
                _f,
                gitee_milestone_id,
            )

    @staticmethod
    def main(product_id=None):
        filter_param = [ Product.is_forced_check.is_(True) ]
        if product_id is not None:
            filter_param.append(Product.id == product_id) 

        products = Product.query.filter(
            *filter_param
        ).all()
        for product in products:
            products_dict = {
                "org_id": product.org_id,
                "product_id": product.id
            }
            UpdateIssueRate.update_product_issue_resolved_rate(
                products=products_dict
            )
            
            rounds = Round.query.filter_by(
                product_id=product.id
            ).all()
            for _r in rounds:
                issue_rate = IssueSolvedRate.query.filter_by(
                    round_id=_r.id, type="round"
                ).first()
                if not issue_rate:
                    Insert(
                        IssueSolvedRate,
                        {
                            "round_id": _r.id,
                            "type": "round",
                        }
                    ).single()
                UpdateIssueRate.update_round_issue_resolved_rate(
                    products=products_dict, round_id=_r.id
                )

            milestones = Milestone.query.filter(
                Milestone.is_sync.is_(True),
                Milestone.product_id == product.id,
                Milestone.round_id != sqlalchemy.null()
            ).all()
            for _m in milestones:
                issue_rate = IssueSolvedRate.query.filter_by(
                    gitee_milestone_id=_m.gitee_milestone_id
                ).first()
                if not issue_rate:
                    Insert(
                        IssueSolvedRate,
                        {
                            "milestone_id": _m.id,
                            "gitee_milestone_id": _m.gitee_milestone_id,
                            "type": "milestone",
                        }
                    ).single(IssueSolvedRate, "/issue_solved_rate")
                UpdateIssueRate.update_milestone_issue_resolved_rate(
                    products=products_dict, gitee_milestone_id=_m.gitee_milestone_id
                )

    @staticmethod
    def statistics(product_id=None):
        filter_param = [ Product.is_forced_check.is_(True) ]
        if product_id is not None:
            filter_param.append(Product.id == product_id) 

        products = Product.query.filter(
            *filter_param
        ).all()

        for product in products:
            products_dict = {
                "org_id": product.org_id,
                "product_id": product.id
            }
            uird = UpdateIssueRateData(products_dict)
            uird.update_issue_resolved_rate_product()
            
            rounds = Round.query.filter_by(
                product_id=product.id
            ).all()
            for _r in rounds:
                issue_rate = IssueSolvedRate.query.filter_by(
                    round_id=_r.id, type="round"
                ).first()
                if not issue_rate:
                    Insert(
                        IssueSolvedRate,
                        {
                            "round_id": _r.id,
                            "type": "round",
                        }
                    ).single()
                uird.update_issue_resolved_rate_round(
                    round_id=_r.id
                )

            milestones = Milestone.query.filter(
                Milestone.is_sync.is_(True),
                Milestone.product_id == product.id,
                Milestone.round_id != sqlalchemy.null()
            ).all()
            for _m in milestones:
                issue_rate = IssueSolvedRate.query.filter_by(
                    gitee_milestone_id=_m.gitee_milestone_id
                ).first()
                if not issue_rate:
                    Insert(
                        IssueSolvedRate,
                        {
                            "milestone_id": _m.id,
                            "gitee_milestone_id": _m.gitee_milestone_id,
                            "type": "milestone",
                        }
                    ).single(IssueSolvedRate, "/issue_solved_rate")
                uird.update_issue_resolved_rate_milestone(
                    milestone_ids=[ _m.gitee_milestone_id ]
                )


class UpdateIssueTypeState(TaskHandlerBase):
    def main(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None,
            Organization.enterprise_token is not None,
        ).all()
        for _org in orgs:
            isa = GiteeV8BaseIssueHandler(org_id=_org.id)
            resp = isa.get_issue_types()
            resp = resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_types = json.loads(
                    resp.get("data")
                ).get("data")
                t_issue_types = []
                for _type in issue_types:
                    t_issue_types.append(
                        {
                            "id": _type.get("id"),
                            "title": _type.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_types(_org.enterprise_id),
                    {"data": json.dumps(t_issue_types)}
                )
            resp = isa.get_issue_states()
            resp = resp.get_json()
            if resp.get("error_code") == RET.OK:
                issue_states = json.loads(
                    resp.get("data")
                ).get("data")

                t_issue_states = []
                for _state in issue_states:
                    t_issue_states.append(
                        {
                            "id": _state.get("id"),
                            "title": _state.get("title"),
                        }
                    )
                redis_client.hmset(
                    RedisKey.issue_states(_org.enterprise_id),
                    {"data": json.dumps(t_issue_states)}
                )
