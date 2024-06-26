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
from contextlib import contextmanager
import pytz

import redis
import requests
from flask import current_app

from celeryservice.tasks import read_openqa_tests_overview
from server.model.product import Product
from server.model.milestone import Milestone
from server.model.testcase import Suite, CaseNode, Baseline
from server.utils.db import Insert, Precise
from server.utils.resource_utils import ResourceManager


class UpdateTaskForm:
    def __init__(self, body):
        self.body = body.__dict__
        self.product_id = None
        self.milestone_id = None
        self.title = None
        self.group = None
        self.baseline_id = None


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

            ResourceManager(
                "product",
                creator_id=form.group.creator_id,
                org_id=form.group.org_id
            ).add_permission(
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
                "start_time": datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai')) + datetime.timedelta(
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
            ResourceManager(
                "milestone",
                creator_id=form.group.creator_id,
                org_id=form.group.org_id
            ).add_permission(
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
            "permission_type": "group",
            "baseline_id": form.baseline_id
        }
        root_case_node = Precise(
            CaseNode, root_case_node_body).first()
        if not root_case_node:
            root_case_node = Insert(CaseNode, root_case_node_body).insert_obj()
        existed_pkgs = []
        for node in root_case_node.children.all():
            if node.type == "suite":
                existed_pkgs.append(node.title)
        for suite in form.body.get("pkgs"):
            # 避免重复创建，需要对pkgs去重
            if suite in existed_pkgs:
                continue
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
                "permission_type": "group",
                "baseline_id": form.baseline_id
            }
            _ = Precise(Milestone, case_node_body).first()
            if not _:
                _ = Insert(CaseNode, case_node_body).insert_obj()
                root_case_node.children.append(_)
        root_case_node.add_update()

    @staticmethod
    def get_baseline_id(form: UpdateTaskForm):
        baseline = Baseline.query.filter_by(milestone_id=form.milestone_id).first()
        if not baseline:
            body = {
                "permission_type": "org",
                "creator_id": form.group.creator_id,
                "group_id": form.group.id,
                "org_id": form.group.org_id,
                "milestone_id": form.milestone_id
            }
            form.baseline_id = Insert(
                Baseline,
                body
            ).insert_id()
        else:
            form.baseline_id = baseline.id


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


class AtHandler:
    def __init__(self, buildname_x86=None, buildname_aarch64=None):
        self.buildname_x86 = buildname_x86 if buildname_x86 else ""
        self.buildname_aarch64 = buildname_aarch64 if buildname_aarch64 else ""
        self.openqa_url = current_app.config.get("OPENQA_URL")

    @staticmethod
    def parse_url(iso_url):
        name_list = iso_url.split("/")
        iso_name = name_list[-1]
        arch = name_list[-2]
        os_name = iso_name.split(f"-{arch}")[0]
        product = os_name.split("-")[0]
        version = os_name.split(f"{product}-")[-1]
        ret = re.search(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}", iso_url)
        return {
            "product": product,
            "version": version,
            "arch": arch,
            "build": ret.group(),
        }

    @contextmanager
    def get_scrapy_redis_cli(self):
        scrapyspider_pool = redis.ConnectionPool.from_url(
            "{}?ssl_cert_reqs=required&ssl_ca_certs=/etc/radiaTest/redis.crt".format(
                current_app.config.get("SCRAPYSPIDER_BACKEND")
            ),
            decode_responses=True
        )
        scrapy_redis_cli = redis.StrictRedis(connection_pool=scrapyspider_pool)
        try:
            yield scrapy_redis_cli
        finally:
            scrapyspider_pool.disconnect()

    def get_build_info(self):
        build_list = list()
        arch_list = []
        if self.buildname_x86:
            x86_parse_info = self.parse_url(self.buildname_x86)
            arch_list.append(x86_parse_info.pop("arch"))
            build_list.append(x86_parse_info)
        if self.buildname_aarch64:
            arm_parse_info = self.parse_url(self.buildname_aarch64)
            arch_list.append(arm_parse_info.pop("arch"))
            build_list.append(arm_parse_info)

        if len(build_list) == 2:
            if build_list[0] == build_list[1]:
                parse_info = build_list[0]
                product = parse_info.get("product")
                version = parse_info.get("version")
                build = parse_info.get("build")
            else:
                return False, {}

        else:
            parse_info = build_list[0]
            product = parse_info.get("product")
            version = parse_info.get("version")
            build = parse_info.get("build")

        return True, {
            "product": product,
            "version": version,
            "arch_list": arch_list,
            "build": build,
        }

    def get_result(self):
        at_result = dict()
        flag, build_info = self.get_build_info()
        if flag is False:
            at_result.update({
                "result": "url err",
                "openqa_url": "",
                "rate": 0
            })
            return True, at_result
        # 获取tests_overview_url 查询所有结果
        product = build_info.get("product")
        version = build_info.get("version")
        arch_list = build_info.get("arch_list")
        build = build_info.get("build")

        tests_overview_url = f"/tests/overview?distri={product.lower()}&version={version}&build=-{build}"
        # 校验是否已触发at任务
        res = requests.get(f"{self.openqa_url}{tests_overview_url}", timeout=30)
        # 不存在直接返回
        if res.status_code != 200:
            at_result.update({
                "result": "no triggered",
                "openqa_url": "",
                "rate": 0
            })
            return True, at_result
        # 存在则获取redis结果
        with self.get_scrapy_redis_cli() as scrapy_redis_cli:
            # 获取所有结果keys
            product_build = f"{product}_{version}_Build-{build}"
            all_test_keys = scrapy_redis_cli.keys(f"{product_build}_*")
            if len(all_test_keys) == 0:
                # 异步执行爬虫爬取数据
                read_openqa_tests_overview.delay(
                    product_build=product_build,
                    tests_overview_url=tests_overview_url
                )
                at_result.update({
                    "result": "in crawling",
                    "openqa_url": "",
                    "rate": 0
                })
                return True, at_result
            else:
                total_job_num = 0
                job_success_num = 0
                job_fail_num = 0
                job_cancel_num = 0
                # 从redis遍历获取所有结果
                for test_key in all_test_keys:
                    for arch in arch_list:
                        res_status = scrapy_redis_cli.hget(test_key, f"{arch}_res_status")
                        if "-" == res_status or res_status is None:
                            continue
                        if ":" in res_status:
                            res_list = res_status.split(": ")
                            state = res_list[0].lower()
                            result = res_list[1].lower()
                        else:
                            state = res_status.lower()
                            result = ""

                        total_job_num += 1
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

                openqa_url = "{}?release_url_x86_64={}&release_url_aarch64={}".format(
                    current_app.config.get("AT_DETAIL"),
                    self.buildname_x86,
                    self.buildname_aarch64
                )
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
        flag, build_info = self.get_build_info()
        total_job_num = 0
        job_success_num = 0
        job_fail_num = 0
        job_cancel_num = 0
        detail_list = []
        arch_list = build_info.get("arch_list", [])
        if flag is True:
            # 获取tests_overview_url 查询所有结果
            product = build_info.get("product")
            version = build_info.get("version")
            build = build_info.get("build")
            detail_dict = dict()
            # 获取存在redis结果
            with self.get_scrapy_redis_cli() as scrapy_redis_cli:
                # 获取所有结果keys
                product_build = f"{product}_{version}_Build-{build}"
                all_test_keys = scrapy_redis_cli.keys(f"{product_build}_*")
                for test_key in all_test_keys:
                    for arch in arch_list:
                        testcase = test_key.split(f"{product_build}_")[-1]
                        res_status = scrapy_redis_cli.hget(test_key, f"{arch}_res_status")
                        if "-" == res_status or res_status is None:
                            continue
                        if ":" in res_status:
                            res_list = res_status.split(": ")
                            state = res_list[0].lower()
                            result = res_list[1].lower()
                        else:
                            state = res_status.lower()
                            result = ""
                        total_job_num += 1
                        if testcase not in detail_dict:
                            detail_dict[testcase] = {}
                        if arch in detail_dict[testcase]:
                            current_app.logger.warning(f"{product_build} {testcase} {arch} is repeat!")
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
            for testcase, case_info in detail_dict.items():
                detail = {"test": testcase}
                for arch, info in case_info.items():
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
