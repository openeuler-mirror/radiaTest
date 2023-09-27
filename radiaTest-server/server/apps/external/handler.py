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

import re
import datetime
import json

from flask import current_app, jsonify, request


from server.model.product import Product
from server.model.milestone import Milestone
from server.model.testcase import Suite, CaseNode
from server.model.job import AtJob
from server.utils.db import Insert, Precise
from server.utils.resource_utils import ResourceManager
from server.utils.response_util import ssl_cert_verify_error_collect, RET
from server.utils.requests_util import do_request
from server.utils.auth_util import generate_messenger_token
from server.schema.job import PayLoad
from server.apps.user.handlers import handler_login
from server.model.organization import Organization


class UpdateTaskForm:
    def __init__(self, body):
        self.body = body.__dict__
        self.product_id = None
        self.milestone_id = None
        self.title = None
        self.group = None


class UpdateTaskHandler:
    @staticmethod
    def get_product_id(form: UpdateTaskForm):
        version = form.body.get("version")
        product_body = {
            "name": form.body.get("product"),
            "version": version
        }
        _product = Precise(Product, product_body).first()

        if not _product:
            if "LTS-SP" in version:
                version_type = "LTS-SPx"
            elif "LTS" in version:
                version_type = "LTS"
            else:
                version_type = "INNOVATION"
            product_body.update(
                {
                    "permission_type": "org",
                    "org_id": form.group.org_id,
                    "version_type": version_type
                }
            )
            form.product_id = Insert(
                Product,
                product_body
            ).insert_id()

            ResourceManager("product", creator_id=form.group.creator_id, org_id=form.group.org_id).add_permission(
                "api_infos.yaml",
                {
                    "creator_id": form.group.creator_id,
                    "org_id": form.group.org_id,
                    "permission_type": "org",
                },
                form.product_id,
            )
        else:
            form.product_id = _product.id

    @staticmethod
    def get_milestone_id(form: UpdateTaskForm):
        _milestone = Milestone.query.filter_by(name=form.title).first()

        if not _milestone:
            body = {
                "name": form.title,
                "product_id": form.product_id,
                "type": "update",
                "is_sync": False,
                "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now() + datetime.timedelta(
                    days=current_app.config.get("OE_QA_UPDATE_TASK_PERIOD")
                )).strftime("%Y-%m-%d %H:%M:%S"),
                "permission_type": "org",
                "creator_id": form.group.creator_id,
                "group_id": form.group.id,
                "org_id": form.group.org_id
            }
            form.milestone_id = Insert(
                Milestone,
                body
            ).insert_id()
            ResourceManager("milestone", creator_id=form.group.creator_id, org_id=form.group.org_id).add_permission(
                "api_infos.yaml",
                {
                    "creator_id": form.group.creator_id,
                    "org_id": form.group.org_id,
                    "permission_type": "org",
                },
                form.milestone_id,
            )
        else:
            form.milestone_id = _milestone.id

    @staticmethod
    def create_case_node(form: UpdateTaskForm):
        milestone = Milestone.query.get(form.milestone_id)
        root_case_node_body = {
            "group_id": form.group.id,
            "title": milestone.name,
            "type": "baseline",
            "milestone_id": milestone.id,
            "org_id": form.group.org_id,
            "permission_type": "group"
        }
        root_case_node = Precise(
            CaseNode, root_case_node_body).first()
        if not root_case_node:
            root_case_node = Insert(CaseNode, root_case_node_body).insert_obj()
        for suite in form.body.get("pkgs"):
            _suite = Suite.query.filter_by(name=suite).first()
            if not _suite:
                _suite = Insert(Suite, {"name": suite}).insert_obj()
            case_node_body = {
                "group_id": form.group.id,
                "title": _suite.name,
                "type": "suite",
                "suite_id": _suite.id,
                "org_id": form.group.org_id,
                "is_root": False,
                "permission_type": "group"
            }
            _ = Precise(Milestone, case_node_body).first()
            if not _:
                _ = Insert(CaseNode, case_node_body).insert_obj()
                root_case_node.children.append(_)
        root_case_node.add_update()


class UpdateRepo:
    def __init__(self, body) -> None:
        self._base_url = body.base_update_url
        self._epol_url = body.epol_update_url

        self.content = ""

    def create_repo_config(self):
        pattern = r'/(update.+?)/'
        result = re.findall(pattern, self._base_url)
        if self._base_url:
            self.content += "[{}]\nname={}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n".format(
                result[-1],
                result[-1],
                self._base_url
            )

        if self._epol_url:
            rs = result[-1].split("_")[-1]
            self.content += "[EPOL-UPDATE-{}]\nname=EPOL-UPDATE-{}\nbaseurl={}$basearch/\nenabled=1\ngpgcheck=0\n\n". \
                format(rs, rs, self._epol_url)


class AtMessenger:
    def __init__(self, body, machine_group):
        self._body = body
        self._body.update({
            "user_id": 1,
        })
        self.machine_group = machine_group

    @ssl_cert_verify_error_collect
    def send_request(self, api, method="post"):
        _resp = dict()
        payload = PayLoad(1, "at")
        token = generate_messenger_token(payload)
        _r = do_request(
            method=method,
            url="https://{}:{}{}".format(
                self.machine_group.messenger_ip,
                self.machine_group.messenger_listen,
                api
            ),
            body=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": request.headers.get("authorization")
            },
            obj=_resp,
            verify=current_app.config.get("CA_CERT"),
        )

        if _r != 0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(_resp)

    def get_job_detail(self, job_id):
        self._body["job_id"] = job_id
        res = self.send_request(f"/api/v1/openeuler/at_job")
        return json.loads(res.get_data(as_text=True)).get("data", {})


class AtHandler:
    def __init__(self, at_messenger, buildname_x86=None, buildname_aarch64=None):
        self.at_messenger = at_messenger
        self.buildname_x86 = buildname_x86 if buildname_x86 else ""
        self.buildname_aarch64 = buildname_aarch64 if buildname_aarch64 else ""

    def get_result(self):
        build_list = list()
        at_result = dict()
        if self.buildname_x86:
            build_list.append(self.buildname_x86)
        if self.buildname_aarch64:
            build_list.append(self.buildname_aarch64)
        at_jobs = AtJob.query.filter(AtJob.build_name.in_(build_list)).all()

        if len(at_jobs) == 0:
            at_result.update({
                "result": "no triggered",
                "openqa_url": "",
                "rate": 0
            })
            return True, at_result
        else:
            total_job_num = 0
            job_success_num = 0
            job_fail_num = 0
            job_cancel_num = 0

            for job in at_jobs:
                if not job.at_job_ids:
                    continue
                at_job_ids = job.at_job_ids.split(",")

                for job_id in at_job_ids:
                    job_detail = self.at_messenger.get_job_detail(job_id)
                    # 排除异常job_id
                    if not job_detail:
                        continue
                    total_job_num += 1
                    state = job_detail.get("state")
                    result = job_detail.get("result")
                    # 任务状态done且结果为passed执行成功
                    if state == "done":
                        if "passed" == result:
                            job_success_num += 1
                        else:
                            job_fail_num += 1
                    elif state == "cancelled":
                        job_cancel_num += 1
                    else:
                        continue

            openqa_url = "https://radiatest.openeuler.org/at-detail?release_url_x86_64={}" \
                         "&release_url_aarch64={}".format(self.buildname_x86, self.buildname_aarch64)
            job_done_num = job_success_num + job_fail_num + job_cancel_num

            if total_job_num == 0:
                at_result.update({
                    "result": "in process",
                    "openqa_url": "",
                    "rate": 0
                })
                return True, at_result
            elif total_job_num != job_done_num:
                at_result.update({
                    "result": "in process",
                    "openqa_url": openqa_url,
                    "rate": round(job_done_num / total_job_num, 2)
                })
                return True, at_result
            else:
                if job_fail_num == 0 and job_cancel_num == 0:
                    result = "passed"
                else:
                    result = "failed"

                at_result.update({
                    "result": result,
                    "openqa_url": openqa_url,
                    "rate": 1
                })

                return True, at_result

    def get_report(self):
        build_list = list()
        detail_dict = dict()
        if self.buildname_x86:
            build_list.append(self.buildname_x86)
        if self.buildname_aarch64:
            build_list.append(self.buildname_aarch64)
        at_jobs = AtJob.query.filter(AtJob.build_name.in_(build_list)).all()
        total_job_num = 0
        job_success_num = 0
        job_fail_num = 0
        job_cancel_num = 0

        for job in at_jobs:
            if not job.at_job_ids:
                continue
            at_job_ids = job.at_job_ids.split(",")

            for job_id in at_job_ids:
                job_detail = self.at_messenger.get_job_detail(job_id)
                # 排除异常job_id
                if not job_detail:
                    continue
                total_job_num += 1
                settings = job_detail.get("settings")
                arch = settings.get("ARCH")
                testcase = settings.get("TEST")
                state = job_detail.get("state")
                result = job_detail.get("result")
                if testcase not in detail_dict:
                    detail_dict[testcase] = {}
                if arch in detail_dict[testcase]:
                    current_app.logger.warning(f"{job_id} arch is repeat!")
                detail_dict[testcase][arch] = {
                    "state": state,
                    "result": result
                }
                # 任务状态done且结果为passed执行成功
                if state == "done":
                    if "passed" == result:
                        job_success_num += 1
                    else:
                        job_fail_num += 1
                elif state == "cancelled":
                    job_cancel_num += 1
                else:
                    continue
        detail_list = []
        arch_list = []
        for testcase, case_info in detail_dict.items():
            detail = {"test": testcase}
            for arch, info in case_info.items():
                if arch not in arch_list:
                    arch_list.append(arch)
                detail[arch] = info
            detail_list.append(detail)
        return {
            "total": total_job_num,
            "success": job_success_num,
            "failed": job_fail_num,
            "canceled": job_cancel_num,
            "detail_list": detail_list,
            "arch_list": sorted(arch_list)
        }


class MajunLoginHandler:
    def __init__(self, type, org_id, access_token):
        authority_map = {
            "openeuler": {"authority": "oneid", "get_user_info_url": "https://omapi.osinfra.cn/oneid/oidc/user"},
            "gitee": {"authority": "gitee", "get_user_info_url": "https://gitee.com/api/v5/user"},
        }
        self._type = type
        self._org_id = org_id
        self._authorty = authority_map.get(self._type)
        self._oauth_token = {"access_token": access_token, "refresh_token": ""}

    def login(self):
        org = Organization.query.filter_by(id=self._org_id, is_delete=0).first()
        if not org:
            return False, "the orgnization is not exists"

        result = handler_login(
            self._oauth_token,
            self._org_id,
            self._authorty.get("get_user_info_url"),
            self._authorty.get("authority")
        )

        if not isinstance(result, tuple) or not isinstance(result[0], bool):
            return False, "get user info error"

        if result[0]:
            return result[0], result[1], result[2], f'{current_app.config["OAUTH_HOME_URL"]}?isSuccess=True'
        else:
            return True, result[1], "", '{}?isSuccess=False&user_id={}&org_id={}&require_cla={}'.format(
                current_app.config["OAUTH_HOME_URL"],
                result[1],
                org.id,
                org.cla_verify_url is not None,
            )