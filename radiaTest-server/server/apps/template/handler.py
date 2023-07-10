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
# @Date    : 2023-05-24
# @License : Mulan PSL v2
#####################################

import os

from flask import current_app

from server.utils.file_util import ExcelImportFile, JsonImportFile
from celeryservice.tasks import resolve_template_testcase
from server.model.template import Template
from server.model.testcase import Case


class TemplateCaseImportHandler:
    def __init__(self, file):
        try:
            _filetype = file.filename.split(".")[-1]
            if _filetype in ["xls", "csv", "xlsx"]:
                self.case_file = ExcelImportFile(file)
            elif _filetype == "json":
                self.case_file = JsonImportFile(file)
            else:
                raise RuntimeError(f"Filetype of {_filetype} not supported")

            if self.case_file.filetype:
                self.case_file.file_save(
                    current_app.config.get("TMP_FILE_SAVE_PATH")
                )
            else:
                mesg = "Filetype of {}.{} is not supported".format(
                    self.case_file.filename,
                    self.case_file.filetype,
                )
                if os.path.exists(self.case_file.filepath):
                    self.case_file.file_remove()
                raise RuntimeError(mesg)

        except RuntimeError as e:
            current_app.logger.error(str(e))
            raise e

    def import_case(self, body):
        resolve_template_testcase.delay(
            filetype=self.case_file.filetype,
            filepath=self.case_file.filepath,
            body=body
        )

    @staticmethod
    def remove_template_cases(template):
        for case in template.cases:
            template.cases.remove(case)
            template.add_update()
        # 循环删除，会遗留一个，单独删除遗留的一个
        if len(template.cases) > 0:
            template.cases.remove(template.cases[0])
        template.add_update()

    @staticmethod
    def add_template_cases(template, cases: list):
        for case_id in cases:
            case = Case.query.filter_by(id=case_id).first()
            if not case:
                continue
            template.cases.append(case)
        template.add_update(Template, "/template")

    @staticmethod
    def update_template_cases(template, cases: list):
        TemplateCaseImportHandler.remove_template_cases(template=template)
        TemplateCaseImportHandler.add_template_cases(template=template, cases=cases)
