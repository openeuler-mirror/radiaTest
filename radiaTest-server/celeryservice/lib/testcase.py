import os
import re
import json
import requests
import shutil

from flask import current_app, jsonify, Response
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from celeryservice.lib import TaskAuthHandler
from server.utils.sheet import Excel, SheetExtractor
from server.utils.response_util import RET, ssl_cert_verify_error_collect
from server.utils.db import Insert, Edit
from server.schema.testcase import BaselineBodyInternalSchema
from server.model.testcase import Suite, Case, Baseline


class TestcaseHandler(TaskAuthHandler):
    def __init__(self, user, logger, promise):
        self.promise = promise
        super().__init__(user, logger)

    def create_baseline(self, body):
        if not body.parent_id:
            baseline_id = Insert(Baseline, body.__dict__).insert_id()
            return baseline_id

        parent = Baseline.query.filter_by(id=body.parent_id).first()
        if not parent:
            raise RuntimeError("parent baseline not exists, creating failed")

        for child in parent.children:
            if body.title == child.title:
                raise RuntimeError(
                    "baseline {} is already exist".format(
                        body.title
                    )
                )

        baseline = Baseline.query.filter_by(
            id=Insert(
                Baseline,
                body.__dict__
            ).insert_id()
        ).first()

        baseline.parent.append(parent)
        baseline.add_update()

        return baseline.id

    def loads_data(self, filetype, filepath):
        excel = Excel(filetype).load(filepath)

        cases = SheetExtractor(
            current_app.config.get("OE_QA_TESTCASE_DICT")
        ).run(excel)

        suites = set()

        for case in cases:
            if not case.get("name") or not case.get("suite") or not case.get("steps") or not case.get("expection") or not case.get("description"):
                continue

            if case.get("automatic") == '是' or case.get("automatic") == 'Y':
                case["automatic"] = True
            else:
                case["automatic"] = False

            _case = Case.query.filter_by(name=case.get("name")).first()

            _suite = Suite.query.filter_by(
                name=case.get("suite")
            ).first()
            if not _suite:
                try:
                    Insert(
                        Suite,
                        {
                            "name": case.get("suite"),
                            "group_id": self.user.get("group_id"),
                            "org_id": self.user.get("org_id"),
                        }
                    ).single(Suite, '/suite')
                    _suite = Suite.query.filter_by(
                        name=case.get("suite")
                    ).first()
                except IntegrityError as e:
                    self.logger.error(f'database operate error -> {e}')
                    raise RuntimeError(f'data has exist / foreign key is bond') from e
                except SQLAlchemyError as e:
                    current_app.logger.error(f'database operate error -> {e}')
                    raise RuntimeError(f'database operate error -> {e}') from e

            case["suite_id"] = _suite.id

            suites.add(_suite.id)

            del case["suite"]

            if not _case:
                Insert(Case, case).single(Case, "/case")

                _case = Case.query.filter_by(name=case.get("name")).first()
            else:
                case["id"] = _case.id

                Edit(Case, case).single(Case, "/case")

        return suites

    def get_baseline_id(self, _title, _type, _parent_id, _suite_id=None, _case_id=None):
        """已存在节点则直接获取id，不存在的节点新增后获取"""

        _body = BaselineBodyInternalSchema(
            title=_title,
            type=_type,
            group_id=self.user.get("group_id"),
            org_id=self.user.get("org_id"),
            parent_id=_parent_id,
            suite_id=_suite_id,
            case_id=_case_id,
            in_set=True,
        )

        filter_params = list()

        if _parent_id is not None:
            parent_baseline = Baseline.query.filter_by(
                id=_parent_id
            ).first()

            if not parent_baseline:
                raise RuntimeError(
                    "parent id {} is not exist.".format(
                        _body.parent_id
                    )
                )

            filter_params = [
                Baseline.title == _body.title,
                Baseline.type == _type,
                Baseline.group_id == self.user.get("group_id"),
                Baseline.org_id == self.user.get("org_id"),
                Baseline.suite_id == _body.suite_id,
                Baseline.case_id == _body.case_id,
                Baseline.parent.contains(parent_baseline),
                Baseline.in_set == True
            ]
        else:
            filter_params = [
                Baseline.title == _body.title,
                Baseline.type == _type,
                Baseline.group_id == self.user.get("group_id"),
                Baseline.org_id == self.user.get("org_id"),
                Baseline.suite_id == _body.suite_id,
                Baseline.case_id == _body.case_id,
                Baseline.in_set == True
            ]

        baseline = Baseline.query.filter(*filter_params).first()

        if baseline:
            return baseline.id
        else:
            _body.update({"permission_type": "group"})
            baseline_id = self.create_baseline(_body)

            return baseline_id

    def travelsal_baseline_tree(self, _file_id, _suites):
        for _suite_id in _suites:
            _suite = Suite.query.filter_by(id=_suite_id).first()

            if not _suite:
                continue

            _this_suite_id = self.get_baseline_id(
                _title=_suite.name,
                _type="suite",
                _suite_id=_suite.id,
                _parent_id=_file_id,
            )

            for case in _suite.case:
                _ = self.get_baseline_id(
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
            _file_id = self.get_baseline_id(
                _name,
                "directory",
                _parent_id,
            )

            body = {
                "file_id": _file_id,
                "filepath": _filepath,
                "group_id": self.user.get("group_id"),
                "user_id": self.user.get("user_id"),
            }

            _verify = True if current_app.config.get("CA_VERIFY") == "True" \
            else current_app.config.get("SERVER_CERT_PATH")

            _resp = requests.post(
                url="https:{}/api/v1/testcase/resolve_by_filepath".format(
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

        _this_id = self.get_baseline_id(
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

    def resolve(self, filepath, file_id=None):
        try:
            self.promise.update_state(
                state="READING",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )

            filetype = os.path.splitext(filepath)[-1]

            pattern = r'^([^(\.|~)].*)\.(xls|xlsx|csv)$'

            if re.match(pattern, os.path.basename(filepath)) is not None:
                suites = self.loads_data(
                    filetype[1:],
                    filepath,
                )

                if isinstance(suites, Response):
                    r = json.loads(suites.response[0])
                    raise RuntimeError(r.get("error_msg"))

                mesg = "File {} has been import".format(
                    os.path.basename(filepath),
                    filetype,
                )

                current_app.logger.info(mesg)

                self.next_period()
                self.promise.update_state(
                    state="RESOLVING",
                    meta={
                        "start_time": self.start_time,
                        "running_time": self.running_time,
                    }
                )

                if file_id is not None:
                    self.travelsal_baseline_tree(file_id, suites)

                self.next_period()
                self.promise.update_state(
                    state="DONE",
                    meta={
                        "start_time": self.start_time,
                        "running_time": self.running_time,
                    }
                )

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

                return jsonify(error_code=RET.OK, error_msg=mesg)

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

        finally:
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)
                if unzip_filepath and os.path.exists(unzip_filepath):
                    if os.path.isdir(unzip_filepath):
                        shutil.rmtree(unzip_filepath)
                    else:
                        os.remove(unzip_filepath)
