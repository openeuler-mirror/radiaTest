import datetime
from typing import List

from flask import current_app

from server.model.product import Product
from server.model.milestone import Milestone
from server.model.testcase import Case, Suite
from server.utils.db import Insert


class UpdateTaskForm:
    def __init__(self, body):
        self._body = body.__dict__
        self.cases = []
        self.product_id = None
        self.milestone_id = None
        self.title = None


class UpdateTaskHandler:
    @staticmethod
    def get_product_id(form):
        _product = Product.query.filter_by(
            name=form._body.get("product"), 
            version=form._body.get("version"),
        ).first()

        if not _product:
            form.product_id = Insert(
                Product, 
                {
                    "name": form._body.get("product"), 
                    "version": form._body.get("version")
                }
            ).insert_id()
        else:
            form.product_id = _product.id

    @staticmethod
    def get_milestone_id(form: UpdateTaskForm):
        _milestone = Milestone.query.filter_by(name=form.title).first()

        if not _milestone:
            form.milestone_id = Insert(
                Milestone, 
                {
                    "name": form.title,
                    "product_id": form.product_id,
                    "type": "update",
                    "start_time": datetime.datetime.now(),
                    "end_time": datetime.datetime.now() + datetime.timedelta(
                        days=current_app.config.get("OE_QA_UPDATE_TASK_PERIOD")
                    )
                }
            ).insert_id()
        else:
            form.milestone_id = _milestone.id

    @staticmethod
    def suites_to_cases(form: UpdateTaskForm):
        for suite in form._body.get("pkgs"):
            _suite = Suite.query.filter_by(name=suite).first()

            if not _suite:
                _suite_id = Insert(Suite, {"name": suite}).insert_id()

                _case_id = Insert(
                    Case, 
                    {
                        "name": "oe_test_{}_cases_implement".format(suite), 
                        "suite_id": _suite_id,
                        "description": "请补充用例",
                        "steps": "1.调研软件包，查阅文档，制定测试方案\n\n2.编写文本用例\n\n3.若可以实现自动化，补充自动化脚本用例，并向代码仓提交PR",
                        "expection": "至少补充文本用例，若可以自动化，并且可开源，则需向代码仓提交PR",
                        "remark": "本用例仅为占位说明，在补充后请手动删除",
                        "automatic": False,
                    }
                ).insert_id()

                if _case_id:
                    form.cases.append(_case_id)
            
            else:
                _cases_object = _suite.case

                _cases_list = [_case.to_json() for _case in _cases_object]

                _cases_name = list(map(lambda case: case["id"], _cases_list))

                form.cases += _cases_name


class UpdateRepo:
    def __init__(self, body) -> None:
        self._base_url = body.base_update_url
        self._epol_url = body.epol_update_url

        self.content = ""

    def create_repo_config(self):
        if self._base_url:
            self.content += "[update]\nname=update\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(self._base_url)
        
        if self._epol_url:
            self.content += "[EPOL-UPDATE]\nname=EPOL-UPDATE\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(self._epol_url)
