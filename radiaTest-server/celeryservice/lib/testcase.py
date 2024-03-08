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

import os
import re
import json
import openpyxl
import requests

from flask import current_app, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from celeryservice.lib import TaskAuthHandler
from server.utils.sheet import Excel, SheetExtractor
from server.utils.response_util import RET, ssl_cert_verify_error_collect
from server.utils.db import Insert
from server.schema.testcase import CaseNodeBodyInternalSchema
from server.model.testcase import Suite, Case, CaseNode
from server.utils.md_util import MdUtil
from server import db
from server.utils.shell import run_cmd


class TestcaseHandler(TaskAuthHandler):
    def __init__(self, user, logger, promise):
        self.promise = promise
        super().__init__(user, logger)

    def create_case_node(self, body):
        if not body.parent_id:
            case_node_id = Insert(CaseNode, body.__dict__).insert_id()
            return case_node_id

        parent = CaseNode.query.filter_by(id=body.parent_id).first()
        if not parent:
            raise RuntimeError("parent case_node not exists, creating failed")

        for child in parent.children:
            if body.title == child.title:
                self.logger.warning("case_node {} is already exist".format(body.title))
                return child.id

        case_node = CaseNode.query.filter_by(
            id=Insert(
                CaseNode,
                body.__dict__
            ).insert_id()
        ).first()

        case_node.parent.append(parent)
        case_node.add_update()

        return case_node.id

    def md2xlsx(self, file):
        _wb_path = os.path.join(current_app.config.get("TMP_FILE_SAVE_PATH"), "testcase", file.name.split('/')[-1])

        wb = openpyxl.Workbook()
        wb.create_sheet(file.name.split('/')[-1])
        wb.save(_wb_path)

        return MdUtil.md2wb(
            md_content=file.read(),
            wb_path=_wb_path,
            sheet_name=file.name.split('/')[-1],
        )

    def loads_data(self, filetype, filepath):
        _filetype = filetype
        _filepath = filepath

        if filetype == "md" or filetype == "markdown":
            with open(filepath, "r") as f:
                _filepath = self.md2xlsx(f)
                _filetype = "xlsx"

        excel = Excel(_filetype).load(_filepath)

        cases = SheetExtractor(
            current_app.config.get("OE_QA_TESTCASE_DICT")
        ).run(excel)

        suites = set()
        caseids = set()
        skip_cases = []

        for case in cases:
            if not case.get("name") or not case.get("suite"):
                skip_cases.append({"case_name": case.get("name"), "suite_name": case.get("suite"),
                                   "filepath": _filepath})
                continue

            if case.get("automatic") == '是' or case.get("automatic") == 'Y' or case.get("automatic") == 'True':
                case["automatic"] = True
            else:
                case["automatic"] = False

            _case = Case.query.filter_by(name=case.get("name")).first()
            if _case and _case.permission_type != self.user.get("permission_type"):
                skip_cases.append({"case_name": case.get("name"), "suite_name": case.get("suite"),
                                   "filepath": _filepath})
                continue

            _suite = Suite.query.filter_by(
                name=case.get("suite")
            ).first()
            if _suite and _suite.permission_type != self.user.get("permission_type"):
                skip_cases.append({"case_name": case.get("name"), "suite_name": case.get("suite"),
                                   "filepath": _filepath})
                continue
            suite_name = ''
            try:
                if not _suite:
                    _suite = Suite(
                        name=case.get("suite"),
                        group_id=self.user.get("group_id"),
                        org_id=self.user.get("org_id"),
                        creator_id=self.user.get("user_id"),
                        permission_type=self.user.get("permission_type"),
                    )
                    db.session.add(_suite)
                    db.session.flush()

                case["suite_id"] = _suite.id

                suites.add(_suite.id)

                suite_name = case.pop("suite")

                if not _case:
                    case["group_id"] = self.user.get("group_id")
                    case["org_id"] = self.user.get("org_id")
                    case["creator_id"] = self.user.get("user_id")
                    case["permission_type"] = self.user.get("permission_type")

                    _case = Case(**case)
                    db.session.add(_case)
                    db.session.flush()
                else:
                    self.logger.warning('testcase  duplication: {}, {}, '.format(suite_name,
                                                                                 case.get("name"), _filepath))
                    for key, value in case.items():
                        setattr(_case, key, value)
                    db.session.add(_case)
                    db.session.flush()

                db.session.commit()
                caseids.add(_case.id)
            except (IntegrityError, SQLAlchemyError) as e:
                self.logger.error(f'database operate error -> {e}')
                db.session.rollback()
                skip_cases.append({"case_name": case.get("name"), "suite_name": suite_name, "filepath": _filepath})
                continue

        return suites, caseids, skip_cases

    def get_case_node_id(self, _title, _type, _parent_id, _suite_id=None, _case_id=None):
        """已存在节点则直接获取id，不存在的节点新增后获取"""

        _body = CaseNodeBodyInternalSchema(
            title=_title,
            type=_type,
            group_id=self.user.get("group_id"),
            org_id=self.user.get("org_id"),
            permission_type=self.user.get("permission_type"),
            parent_id=_parent_id,
            suite_id=_suite_id,
            case_id=_case_id,
            in_set=True,
        )

        filter_params = list()

        if _parent_id is not None:
            parent_case_node = CaseNode.query.filter_by(
                id=_parent_id
            ).first()

            if not parent_case_node:
                raise RuntimeError(
                    "parent id {} is not exist.".format(
                        _body.parent_id
                    )
                )

            filter_params = [
                CaseNode.title == _body.title,
                CaseNode.type == _type,
                CaseNode.group_id == self.user.get("group_id"),
                CaseNode.org_id == self.user.get("org_id"),
                CaseNode.permission_type == self.user.get("permission_type"),
                CaseNode.suite_id == _body.suite_id,
                CaseNode.case_id == _body.case_id,
                CaseNode.parent.contains(parent_case_node),
                CaseNode.in_set == True
            ]
        else:
            filter_params = [
                CaseNode.title == _body.title,
                CaseNode.type == _type,
                CaseNode.group_id == self.user.get("group_id"),
                CaseNode.org_id == self.user.get("org_id"),
                CaseNode.permission_type == self.user.get("permission_type"),
                CaseNode.suite_id == _body.suite_id,
                CaseNode.case_id == _body.case_id,
                CaseNode.in_set == True
            ]

        case_node = CaseNode.query.filter(*filter_params).first()

        if case_node:
            return case_node.id
        else:
            case_node_id = self.create_case_node(_body)

            return case_node_id

    def travelsal_case_node_tree(self, _parent_id, _suites, cases):
        for _suite_id in _suites:
            _suite = Suite.query.filter_by(id=_suite_id).first()

            if not _suite:
                continue

            _this_suite_id = self.get_case_node_id(
                _title=_suite.name,
                _type="suite",
                _suite_id=_suite.id,
                _parent_id=_parent_id,
            )
            for case_id in cases:
                case = Case.query.get(case_id)
                if not case:
                    continue
                if case in _suite.case:
                    _ = self.get_case_node_id(
                        _title=case.name,
                        _type="case",
                        _parent_id=_this_suite_id,
                        _case_id=case.id,
                    )

    @ssl_cert_verify_error_collect
    def deep_create(self, _filepath, _parent_id):
        _title = ""
        if not _parent_id:
            _title = "用例集"
        else:
            _title = os.path.basename(_filepath)

        _name = os.path.basename(_filepath).split('.')[0]
        _ext = os.path.basename(_filepath).split('.')[-1]

        if os.path.isfile(_filepath) and _ext in ['xlsx', 'xls', 'csv'] and _name:
            _parent_id = self.get_case_node_id(
                _name,
                "directory",
                _parent_id,
            )

            body = {
                "parent_id": _parent_id,
                "filepath": _filepath,
                "group_id": self.user.get("group_id"),
                "user_id": self.user.get("user_id"),
            }

            _verify = True if current_app.config.get("CA_VERIFY") == "True" \
                else current_app.config.get("CA_CERT")

            _resp = requests.post(
                url="https://{}/api/v1/testcase/resolve-by-filepath".format(
                    current_app.config.get("SERVER_ADDR"),
                ),
                data=json.dumps(body),
                headers={
                    'Content-Type': 'application/json;charset=utf8',
                    'Authorization': self.user.get("auth"),
                },
                verify=_verify,
            )
            if isinstance(_resp, dict):
                self.logger.error(
                    f"messenger: {_resp}"
                )
                return

            if _resp.status_code == 200:
                resp_dict = json.loads(_resp.text)
                if resp_dict.get("data"):
                    self.save_task_to_db(
                        resp_dict["data"]["tid"],
                        f"resolve testcase {os.path.basename(_filepath)}",
                    )
                else:
                    self.logger.error(resp_dict["error_msg"])
            else:
                try:
                    try:
                        msg = json.loads(_resp.text).get("message")
                    except:
                        msg = _resp.text
                    self.logger.error(
                        f"Bad request post to server api for resolve testcase by filepath: {msg}"
                    )
                except:
                    self.logger.error(
                        "Bad request post to server api for resolve testcase by filepath")
            return

        if not os.path.isdir(_filepath):
            self.logger.warning(
                f"{_filepath} is not a directory or a supported file"
            )
            return

        _this_id = self.get_case_node_id(
            _title=_title,
            _type="directory",
            _parent_id=_parent_id,
        )

        subfiles = os.listdir(_filepath)

        for subfile in subfiles:
            self.deep_create(
                _filepath="{}/{}".format(_filepath, subfile),
                _parent_id=_this_id,
            )

    def resolve(self, filepath, parent_id=None):
        try:
            self.promise.update_state(
                state="READING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )

            filetype = os.path.splitext(filepath)[-1]

            pattern = r'^([^(\.|~)].*)\.(xls|xlsx|csv|md|markdown)$'
            if re.match(pattern, os.path.basename(filepath)) is not None:
                suites, cases, skip_cases = self.loads_data(
                    filetype[1:],
                    filepath,
                )

                mesg = "File {} has been import".format(os.path.basename(filepath))
                current_app.logger.warning(mesg)
                if skip_cases:
                    current_app.logger.warning(f"{os.path.basename(filepath)}, skip_cases: {skip_cases}")

                self.next_period()
                self.promise.update_state(
                    state="RESOLVING",
                    meta={
                        "start_time": self.start_time,
                        "running_time": self.running_time,
                    }
                )

                if parent_id is not None:
                    self.travelsal_case_node_tree(parent_id, suites, cases)

                self.next_period()
                self.promise.update_state(
                    state="DONE",
                    meta={
                        "start_time": self.start_time,
                        "running_time": self.running_time,
                    }
                )
                self.clean_file(filepath)
                return jsonify(
                    error_code=RET.OK,
                    error_msg=mesg,
                    data=list(suites)
                )

            else:
                mesg = "File {} is not supported".format(
                    os.path.basename(filepath),
                )

                current_app.logger.error(mesg)

                self.next_period()
                self.promise.update_state(
                    state="FAILURE",
                    meta={
                        "start_time": self.start_time,
                        "running_time": self.running_time,
                    }
                )
                # 清理解析文件
                self.clean_file(filepath)
                return jsonify(error_code=RET.OK, error_msg=mesg)

        except Exception as e:
            current_app.logger.error(str(e))

            self.next_period()
            self.promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )
            # 清理解析文件
            self.clean_file(filepath)
            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))

    def resolve_case_set(self, zip_filepath, unzip_filepath):
        try:
            self.promise.update_state(
                state="CREATING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )

            self.deep_create(
                _filepath=unzip_filepath,
                _parent_id=None,
            )

            self.next_period()
            self.promise.update_state(
                state="SUCCESS",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )

            return jsonify(error_code=RET.OK, error_msg="OK")

        except RuntimeError as e:
            current_app.logger.error(str(e))

            self.next_period()
            self.promise.update_state(
                state="FAILURE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )

            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))

    @staticmethod
    def clean_file(filepath):
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as error:
                # 用例集导入文件为uncompress用户权限
                current_app.logger.error(str(error))
                _, _, _ = run_cmd("sudo -u uncompress rm -rf '{}'".format(filepath))
