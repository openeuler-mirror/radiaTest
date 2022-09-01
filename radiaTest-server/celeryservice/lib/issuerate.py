import json
from celery import current_app as celery
import sqlalchemy
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server.utils.db import Insert, Edit, collect_sql_error
from server import db
from server.model.milestone import Milestone, IssueSolvedRate
from server.model.organization import Organization
from server.model.product import Product
from server.apps.milestone.handler import IssueStatisticsHandlerV8, IssueOpenApiHandlerV8
from celeryservice.lib import TaskHandlerBase


class UpdateIssueRateData:
    def __init__(self, gitee_id, products):
        self.gitee_id = gitee_id
        self.products = products
        self.issue_v8 = IssueStatisticsHandlerV8(
            gitee_id=gitee_id, org_id=products.get("org_id")
        )

        self.param = {
            "serious_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": 4,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": 4,
                    "issue_state_ids": self.issue_v8.serious_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "fields": {
                    "serious_resolved_rate": ""
                }
            },
            "main_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": 3,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": 3,
                    "issue_state_ids": self.issue_v8.serious_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "fields": {
                    "main_resolved_rate": ""
                }
            },
            "serious_main_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "priority": "3,4",
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "priority": "3,4",
                    "issue_state_ids": self.issue_v8.serious_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "fields": {
                    "serious_main_resolved_rate": "",
                    "serious_main_resolved_cnt": "",
                    "serious_main_all_cnt": "",
                }
            },
            "current_resolved_rate": {
                "all": {
                    "milestone_id": "",
                    "issue_state_ids": self.issue_v8.all_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "part": {
                    "milestone_id": "",
                    "issue_state_ids": self.issue_v8.current_resolved_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "fields": {
                    "current_resolved_rate": "",
                    "current_resolved_cnt": "",
                    "current_all_cnt": "",
                }
            },
            "left_issues_cnt": {
                "all": {
                    "milestone_id": "",
                    "issue_state_ids": self.issue_v8.left_state_ids,
                    "issue_type_id": self.issue_v8.bug_issue_type_id,
                },
                "fields": {
                    "left_issues_cnt": ""
                }
            },

        }

    def update_product_issue_resolved_rate(self, field: str):
        milestones = Milestone.query.filter_by(
            product_id=self.products.get("product_id"), is_sync=True
        ).all()
        if not milestones:
            return
        param1 = self.param.get(field).get("all")
        if not param1:
            return
        issue_resolved_rate_dict = dict()
        issue_resolved_rate_dict.update(
            {
                "id": self.products.get("product_id"),
            }
        )
        milestone_ids = ""
        for _milestone in milestones:
            milestone_ids = ",".join(
                [milestone_ids, str(_milestone.gitee_milestone_id)]
            )

        param1.update({"milestone_id": milestone_ids})
        all_cnt = self.issue_v8.get_issues_cnt(param1)
        if not all_cnt:
            return

        param2 = self.param.get(field).get("part")
        if param2:
            param2.update({"milestone_id": milestone_ids})
            resolved_cnt = self.issue_v8.get_issues_cnt(param2)
            resolved_rate = None
            if resolved_cnt and all_cnt and int(all_cnt) != 0:
                resolved_rate = int(resolved_cnt) / int(all_cnt)
            if resolved_rate:
                resolved_rate = "%.f%%" % (resolved_rate * 100)
            else:
                return

            issue_resolved_rate_dict.update(
                {field: resolved_rate}
            )
        else:
            issue_resolved_rate_dict.update(
                {field: all_cnt}
            )
        Edit(Product, issue_resolved_rate_dict).single(Product, "/product")

    def update_milestone_issue_resolved_rate(self,  gitee_milestone_id, field: str):
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
        if not all_cnt:
            return
        if not resolved_cnt and param2:
            return

        issue_resolved_rate_dict = dict()
        _m = Milestone.query.filter_by(
            gitee_milestone_id=gitee_milestone_id).first()
        issue_resolved_rate_dict.update(
            {
                "milestone_id": _m.id,
                "gitee_milestone_id": gitee_milestone_id,
            }
        )
        _issuerate_dict = self.param.get(field).get("fields")
        for k in _issuerate_dict.keys():
            if "resolved_rate" in k:
                issue_resolved_rate_dict.update({k: resolved_rate})
            if "resolved_cnt" in k:
                issue_resolved_rate_dict.update({k: resolved_cnt})
            if "all_cnt" in k:
                issue_resolved_rate_dict.update({k: all_cnt})

        issue_rate = IssueSolvedRate.query.filter_by(
            gitee_milestone_id=gitee_milestone_id).first()
        if issue_rate:
            issue_resolved_rate_dict.update({"id": issue_rate.id})
            Edit(IssueSolvedRate, issue_resolved_rate_dict).single(
                IssueSolvedRate, "/issue_solved_rate")


@celery.task
def update_field_issue_rate(obj_type: str, gitee_id, products: dict, field: str, gitee_milestone_id=None):
    _uird = UpdateIssueRateData(gitee_id, products)
    if obj_type == "product":
        _uird.update_product_issue_resolved_rate(field)
    elif obj_type == "milestone":
        _uird.update_milestone_issue_resolved_rate(gitee_milestone_id, field)


class UpdateIssueRate(TaskHandlerBase):
    @staticmethod
    def update_product_issue_resolved_rate(gitee_id, products: dict):
        fields = ["serious_resolved_rate", "serious_main_resolved_rate",
                  "current_resolved_rate", "left_issues_cnt"]
        for _f in fields:
            update_field_issue_rate.delay(
                "product",
                gitee_id,
                products,
                _f
            )

    @staticmethod
    def update_milestone_issue_resolved_rate(gitee_id, products: dict, gitee_milestone_id):
        fields = ["serious_resolved_rate", "main_resolved_rate", "serious_main_resolved_rate",
                  "current_resolved_rate", "left_issues_cnt"]
        for _f in fields:
            update_field_issue_rate.delay(
                "milestone",
                gitee_id,
                products,
                _f,
                gitee_milestone_id,
            )

    def main(self):
        products = Product.query.order_by(Product.org_id).all()
        t_org_id = -1
        for _p in products:
            if _p.org_id != t_org_id:
                gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_p.org_id)
            if gitee_id:
                products = {
                    "org_id": _p.org_id,
                    "product_id": _p.id
                }
                UpdateIssueRate.update_product_issue_resolved_rate(
                    gitee_id=gitee_id, products=products
                )

                milestones = Milestone.query.filter_by(
                    is_sync=True, product_id=_p.id
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
                                "gitee_milestone_id": _m.gitee_milestone_id
                            }
                        ).single(IssueSolvedRate, "/issue_solved_rate")
                    UpdateIssueRate.update_milestone_issue_resolved_rate(
                        gitee_id=gitee_id, products=products, gitee_milestone_id=_m.gitee_milestone_id
                    )
            t_org_id = _p.org_id


class UpdateIssueTypeState(TaskHandlerBase):
    def main(self):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        orgs = Organization.query.filter(
            Organization.enterprise_id is not None).all()
        for _org in orgs:
            gitee_id = IssueStatisticsHandlerV8.get_gitee_id(_org.id)
            if gitee_id:
                isa = IssueOpenApiHandlerV8(gitee_id=gitee_id)
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
                        {"data": t_issue_types}
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
                        {"data": t_issue_states}
                    )
