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
# @Date    : 2023/05/24
# @License : Mulan PSL v2
#####################################
import json
import io

from flask import current_app

from server.utils.sheet import Excel, SheetExtractor
from server.model.testcase import Case, Suite
from server.model.template import Template
from celeryservice.lib import TaskHandlerBase


class TemplateCaseHandler(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def import_cases_to_template(self, filetype, filepath, body):
        _filetype = filetype
        _filepath = filepath
        if _filetype in ["xls", "csv", "xlsx"]:
            excel = Excel(_filetype).load(_filepath)

            cases = SheetExtractor(
                current_app.config.get("OE_QA_TESTCASE_DICT")
            ).run(excel)
        elif _filetype == "json":
            with io.open(file=filepath, mode="r", encoding="utf-8") as f:
                content = json.loads(f.read())
                cases = content.get("cases")
        else:
            return
        template = Template.query.filter_by(name=body.get("name")).first()
        for case in cases:
            if not case.get("name"):
                continue

            _case = Case.query.join(Suite).filter(
                Case.name == case.get("name"),
                Case.suite_id == Suite.id,
                Suite.git_repo_id == body.get("git_repo_id")
            ).first()
            if _case:
                template.cases.append(_case)
        template.add_update(Template, "/template")
