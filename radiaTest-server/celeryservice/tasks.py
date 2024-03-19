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
import ssl
import re
from datetime import datetime
import os
import sys
import json
import requests
from lxml import html, etree

import redis
from celery import current_app as celery
from celery.utils.log import get_task_logger
from celery.signals import task_postrun
from celery.schedules import crontab

from server import redis_client
from server.model.framework import GitRepo
from server.model.testcase import Suite
from server.model.celerytask import CeleryTask
from server.utils.db import Insert
from server.utils.shell import add_escape, run_cmd
from server import db
from celeryservice import celeryconfig
from celeryservice.lib.repo.handler import RepoTaskHandler
from celeryservice.lib.issuerate import UpdateIssueRate, UpdateIssueTypeState
from celeryservice.lib.testcase import TestcaseHandler
from celeryservice.lib.dailybuild import DailyBuildHandler
from celeryservice.lib.rpmcheck import RpmCheckHandler
from celeryservice.lib.casenode import CaseNodeCreator
from celeryservice.lib.task import TaskdistributeHandler, VersionTaskProgressHandler, AllVersionTaskProgressHandler
from celeryservice.lib.baseline_template import ResolveBaseNodeHandler
from server.utils.openqa_util import RedisPipeline
from server.schema.openqa import (
    OpenqaHomeItem,
    OpenqaGroupOverviewItem,
    OpenqaTestsOverviewItem
)
from server.plugins.flask_socketio import SocketIO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

logger = get_task_logger("manage")
socketio = SocketIO(message_queue=celeryconfig.socketio_pubsub, ssl={"ssl": {"cert_reqs": ssl.CERT_NONE}})

# 建立redis backend连接池
pool = redis.ConnectionPool.from_url(celeryconfig.result_backend, decode_responses=True)
# 建立scrapyspider的存储redis池
scrapyspider_pool = redis.ConnectionPool.from_url(
    celeryconfig.scrapyspider_backend,
    decode_responses=True
)


@task_postrun.connect
def close_session(*args, **kwargs):
    db.session.remove()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0, async_update_celerytask_status.s(), name="update_celerytask_status"
    )
    sender.add_periodic_task(
        crontab(minute=0, hour=0), async_update_all_issue_rate.s(), name="update_all_issue_rate"
    )
    sender.add_periodic_task(
        crontab(minute=0, hour=0, day_of_month="15,30"), async_update_issue_type_state.s(),
        name="update_issue_type_state"
    )
    sender.add_periodic_task(
        crontab(minute="*/60"), async_read_openqa_homepage.s(), name="read_openqa"
    )

    sender.add_periodic_task(
        crontab(minute="*/60"),
        async_update_all_task_progress.s(),
        name="update_all_task_progress",
    )


@celery.task
def async_read_openqa_homepage():
    response = requests.get(f"{celeryconfig.openqa_url}")
    html_content = response.text

    # 使用 lxml 解析网页内容
    tree = html.fromstring(html_content)

    results = tree.xpath('//div[@id="content"]/h2')
    _redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
    redis_pipeline = RedisPipeline(_redis_client)
    for result in results:
        item = {}
        item["product_name"] = result.xpath('./a/text()')[0]
        item["group_overview_url"] = result.xpath('./a/@href')[0]
        home_page_data = OpenqaHomeItem(**item)
        _ = redis_pipeline.process_item(home_page_data)

    _keys = _redis_client.keys("*_group_overview_url")

    if not _keys:
        logger.warning("No products on openQA homepage, or the openQA server met some problems")
        return

    logger.info("crawl data from openQA homepage succeed")

    for _key in _keys:
        group_overview_url = _redis_client.get(_key)
        product_name = _key.split("_group_overview_url")[0]

        logger.info(f"crawl group overview data of product {product_name}")

        read_openqa_group_overview.delay(
            product_name=product_name,
            group_overview_url=group_overview_url
        )


@celery.task
def read_openqa_group_overview(product_name, group_overview_url):
    response = requests.get(f"{celeryconfig.openqa_url}{add_escape(group_overview_url)}?limit_builds=400")
    html_content = response.text

    # 使用 lxml 解析网页内容
    tree = html.fromstring(html_content)
    results = tree.xpath('//div[@id="build-results"]/div[@class="row build-row no-children"]')
    _redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
    _redis_pipeline = RedisPipeline(_redis_client)

    for result in results:
        item = {}
        item["product_name"] = product_name

        title = result.xpath('./div[@class="col-lg-4 text-nowrap"]/span[@class="h4"]')[0]

        item["build_name"] = title.xpath('./a/text()')[0]
        item["build_tests_url"] = title.xpath('./a/@href')[0]
        item["build_time"] = title.xpath('./abbr/@title')[0]
        group_overview_data = OpenqaGroupOverviewItem(**item)
        _ = _redis_pipeline.process_item(group_overview_data)

    logger.info(f"crawl group overview data of product {product_name} succeed")

    _keys = _redis_client.keys(f"{product_name}_*_tests_overview_url")
    for _key in _keys:
        tests_overview_url = _redis_client.get(_key)
        product_build = _key.split("_tests_overview_url")[0]

        logger.info(f"crawl tests overview data of product {product_build}")

        read_openqa_tests_overview.delay(
            product_build=product_build,
            tests_overview_url=tests_overview_url
        )


@celery.task
def read_openqa_tests_overview(product_build, tests_overview_url):
    response = requests.get(f"{celeryconfig.openqa_url}{tests_overview_url}")
    html_content = response.text

    # 使用 lxml 解析网页内容
    tree = html.fromstring(html_content)
    test_overview_parse(tree, product_build)

    logger.info(f"crawl tests overview data of product {product_build} succeed")


@celery.task
def async_update_celerytask_status():
    # 创建redis client连接实例
    _redis_client = redis.StrictRedis(connection_pool=pool)

    # 查询数据库持久化存储的celery task
    _tasks = CeleryTask.query.all()

    for _task in _tasks:
        str_t = _redis_client.get("celery-task-meta-{}".format(_task.tid))

        if not str_t:
            db.session.delete(_task)
        else:
            dict_t = json.loads(str_t)

            if not dict_t.get("status"):
                _task.delete(CeleryTask, "/celerytask", True)
            else:
                _task.status = dict_t["status"]

                if dict_t.get("result"):
                    _result = dict_t["result"]
                    if _result.get("start_time"):
                        _task.start_time = _result["start_time"]
                    if _result.get("running_time"):
                        _task.running_time = _result["running_time"]

    db.session.commit()

    socketio.emit("update", namespace="/celerytask", broadcast=True)


@celery.task
def async_update_all_task_progress():
    AllVersionTaskProgressHandler(logger).update_all_version_task_progress()


@celery.task(bind=True)
def update_task_progress(self, task_id):
    VersionTaskProgressHandler(logger, self).update_version_task_progress(task_id)


@celery.task
def async_update_all_issue_rate(product_id=None):
    UpdateIssueRate.statistics(product_id)


@celery.task(bind=True)
def load_scripts(self, id_, name, url, branch):
    lock_key = f"loading_repo#{id_}_{url}@{branch}"
    logger.info(f"begin loading repo #{id_} from {url} on {branch}, locked...")
    redis_client.set(lock_key, 1)

    try:
        RepoTaskHandler(logger, self).main(id_, name, url, branch)
        logger.info(f"loading repo #{id_} from {url} on {branch} succeed")

    finally:
        redis_client.delete(lock_key)
        logger.info(f"the lock of loading repo #{id_} from {url} on {branch} has been removed")


@celery.task
def async_read_git_repo():
    repos = GitRepo.query.filter_by(adaptive=True).all()

    for repo in repos:
        if not repo.adaptive or redis_client.get(f"loading_repo#{repo.id}_{repo.git_url}@{repo.branch}"):
            continue

        _task = load_scripts.delay(
            repo.id,
            repo.name,
            repo.git_url,
            repo.branch,
        )

        logger.info(f"task id: {_task.task_id}")

        celerytask = {
            "tid": _task.task_id,
            "status": "PENDING",
            "object_type": "scripts_load",
            "description": f"from {repo.git_url} on branch {repo.branch}",
        }

        _ = Insert(CeleryTask, celerytask).single(CeleryTask, "/celerytask")


@celery.task(bind=True)
def resolve_testcase_file(self, filepath, user, parent_id=None):
    TestcaseHandler(user, logger, self).resolve(
        filepath,
        parent_id
    )


@celery.task(bind=True)
def resolve_testcase_set(self, zip_filepath, unzip_filepath, user):
    TestcaseHandler(user, logger, self).resolve_case_set(
        zip_filepath,
        unzip_filepath,
    )


@celery.task
def resolve_distribute_template(task_id, template_id, body):
    TaskdistributeHandler(logger).distribute(
        task_id=task_id,
        template_id=template_id,
        body=body,
    )


@celery.task
def resolve_base_node(body):
    ResolveBaseNodeHandler(logger).create_base_node(
        body=body,
    )


@celery.task
def async_update_issue_type_state():
    UpdateIssueTypeState(logger).main()


@celery.task(bind=True)
def resolve_dailybuild_detail(self, dailybuild_id, dailybuild_detail, weekly_health_id):
    DailyBuildHandler(logger, self).resolve_detail(
        dailybuild_id,
        dailybuild_detail,
        weekly_health_id,
    )


@celery.task(bind=True)
def resolve_rpmcheck_detail(self, build_name, rpm_check_detail, _file=None):
    RpmCheckHandler(logger, self).resolve_detail(
        build_name,
        rpm_check_detail,
        _file,
    )


@celery.task
def resolve_pkglist_after_resolve_rc_name(repo_url, store_path, product, round_num=None):
    if not repo_url or not store_path or not product:
        logger.error("neither param repo_url store_path product could be None.")
        return

    _repo_url = repo_url
    product_version = f"{store_path}/{product}"
    repo_paths = ["everything", "EPOL/main", "update"]
    if round_num:
        product_version = f'{product_version}-round-{round_num}'
        resp = requests.get(repo_url)
        if resp.status_code != 200:
            logger.error("Could not connect to the url: {}".format(repo_url))
            return
        resp.encoding = 'utf-8'
        # 网页内容到写入文件中
        tmp_file_name = f"{product_version}-html.txt"
        with open(tmp_file_name, "wb") as f:
            f.write(resp.content)
            f.close()
        exitcode, output, error = run_cmd(f"cat {tmp_file_name} | grep 'rc{round_num}_openeuler'"
                                          + " | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | uniq"
                                          )

        if exitcode != 0:
            logger.error(error)
            return
        _repo_url = f'{_repo_url}/{output}'
        repo_paths = repo_paths[:-1]

    def get_pkg_file(url, tmp_file_name, pkg_file):
        resp = requests.get(url)
        if resp.status_code != 200:
            logger.error("Could not connect to the url: {}".format(url))
            return
        resp.encoding = 'utf-8'
        # 写入网页内容到文件中
        with open(tmp_file_name, "wb") as f:
            f.write(resp.content)
            f.close()
        exitcode, _, error = run_cmd(f"cat {tmp_file_name} | "
                                     + "grep 'title=' | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | grep '.rpm' | uniq >"
                                     + f"{pkg_file}"
                                     )

        if exitcode != 0:
            logger.error(error)
            return

    for repo_path in repo_paths:
        product_version_repo = f"{product_version}-{repo_path.split('/')[0]}"
        for arch in ["aarch64", "x86_64"]:
            _url = f"{_repo_url}/{repo_path}/{arch}/Packages/"
            tmp_file_name = f"{product_version_repo}-{arch}-html.txt"
            pkg_file = f"{product_version_repo}-{arch}.pkgs"
            get_pkg_file(_url, tmp_file_name, pkg_file)
        exitcode, _, error = run_cmd(f"sort {product_version_repo}-aarch64.pkgs"
                                     + f" {product_version_repo}-x86_64.pkgs | uniq >{product_version_repo}-all.pkgs"
                                     )

        if exitcode != 0:
            logger.error(error)
            return

    _url = f"{_repo_url}/source/Packages/"
    tmp_file_name = f"{product_version}-source-html.txt"
    pkg_file = f"{product_version}-source.pkgs"
    get_pkg_file(_url, tmp_file_name, pkg_file)
    _, _, _ = run_cmd(f"rm -f {store_path}/{product}*html.txt")

    logger.info(f"crawl openeuler's packages list of {product} succeed")
    lock_key = f"resolving_{product}-release_pkglist"
    if round_num is not None:
        lock_key = f"resolving_{product}-round-{round_num}_pkglist"
    redis_client.delete(lock_key)
    logger.info(f"the lock of crawling has been removed")


@celery.task
def resolve_pkglist_from_url(repo_name, repo_url, store_path):
    if not repo_url or not repo_name or not store_path:
        logger.error("neither param repo_name, repo_url could be None.")
        return

    for repo_path in ["everything", "EPOL/main"]:
        _repo_path = f"{repo_name}-{repo_path.split('/')[0]}"
        for arch in ["aarch64", "x86_64"]:
            _url = f"{repo_url}/{repo_path}/{arch}/Packages/"
            resp = requests.get(_url)
            if resp.status_code != 200:
                logger.error("Could not connect to the url: {}".format(_url))
                return
            resp.encoding = 'utf-8'
            # 写入网页内容到文件中
            tmp_file_name = f"{store_path}/{_repo_path}-{arch}-html.txt"
            with open(tmp_file_name, "wb") as f:
                f.write(resp.content)
                f.close()

            exitcode, _, error = run_cmd(f"cat {tmp_file_name} | "
                                         + "grep 'title=' | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | grep '.rpm' | uniq >"
                                         + f"{store_path}/{_repo_path}-{arch}.pkgs"
                                         )

            if exitcode != 0:
                logger.error(error)
                return
        exitcode, _, error = run_cmd(f"sort {store_path}/{_repo_path}-aarch64.pkgs"
                                     + f" {store_path}/{_repo_path}-x86_64.pkgs | uniq >{store_path}/{_repo_path}-all.pkgs"
                                     )

        if exitcode != 0:
            logger.error(error)
            return
    _, _, _ = run_cmd(f"rm -f {store_path}/{repo_name}*html.txt")

    logger.info(f"crawl openeuler's packages list of {repo_name} succeed")
    lock_key = f"resolving_{repo_name}_pkglist"
    redis_client.delete(lock_key)
    logger.info(f"the lock of crawling has been removed")


@celery.task(bind=True)
def async_create_testsuite_node(
        self,
        parent_id: int,  # 被创建suite类型节点的父节点
        suite_id: int,  # 被创建suite类型节点关联的用例ID
        permission_type: str = 'public',  # 被创建suite类型节点的权限类型
        org_id: int = None,  # 被创建suite类型节点的所属组织
        group_id: int = None,  # 被创建suite类型节点的所属团队
        user_id: str = None,  # 创建异步任务的当前用户id
):
    testsuite_node_id = CaseNodeCreator(logger, self).create_suite_node(
        parent_id,
        suite_id,
        permission_type,
        org_id,
        group_id,
        user_id,
    )
    if not testsuite_node_id:
        return

    suite = Suite.query.filter_by(id=suite_id).first()
    # 分发创建对应测试套下用例节点子任务
    for testcase in suite.case:
        _task = async_create_testcase_node.delay(
            testsuite_node_id,
            testcase.name,
            testcase.id,
            permission_type,
            org_id,
            group_id
        )
        celerytask = {
            "tid": _task.task_id,
            "status": "PENDING",
            "object_type": "create_testcase_node",
            "description": f"create case node related to case#{testcase.id} under {suite.name}",
            "user_id": user_id,
        }

        _ = Insert(CeleryTask, celerytask).single(CeleryTask, "/celerytask")


@celery.task(bind=True)
def async_create_testcase_node(
        self,
        parent_id: int,  # 被创建case类型节点的父节点
        case_name: str,  # 被创建case类型节点关联的用例名
        case_id: int,  # 被创建case类型节点关联的用例ID
        permission_type: str = 'public',  # 被创建case类型节点的权限类型
        org_id: int = None,  # 被创建case类型节点的所属组织
        group_id: int = None,  # 被创建case类型节点的所属团队
):
    CaseNodeCreator(logger, self).create_case_node(
        parent_id,
        case_name,
        case_id,
        permission_type,
        org_id,
        group_id,
    )


def get_test_time_by_res_log(res_log):
    start_time = "-"
    end_time = "-"
    test_duration = "-"
    res = re.match("/tests/(?P<job_id>\d+)", res_log)
    if res:
        try:
            job_id = res.group("job_id")
            job_detail_url = f"{celeryconfig.openqa_url}/api/v1/jobs/{job_id}"
            resp = requests.request("get", job_detail_url)
            job_data = resp.json()["job"]
            start_date = datetime.strptime(job_data.get("t_started", "-"), "%Y-%m-%dT%H:%M:%S")
            end_date = datetime.strptime(job_data.get("t_finished", "-"), "%Y-%m-%dT%H:%M:%S")
            if start_date:
                start_time = start_date.strftime("%Y-%m-%d %H:%M:%S")
            if end_date:
                end_time = end_date.strftime("%Y-%m-%d %H:%M:%S")
            if end_date > start_date:
                test_duration = (end_date - start_date).seconds
        except Exception as err:
            logger.error(f"获取测试时间失败， {err}")

    return start_time, end_time, test_duration


def test_overview_parse(tree, product_build):
    _redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
    _redis_pipeline = RedisPipeline(_redis_client)
    results = tree.xpath('//table[@id="results_dvd"]/tbody/tr')

    for result in results:
        item = {}
        item["product_build"] = product_build
        item["test"] = result.xpath('./td[@class="name"]/span/text()')[0]
        item["aarch64_res_status"] = "-"
        item["aarch64_res_log"] = "-"
        item["aarch64_failedmodule_name"] = "-"
        item["aarch64_failedmodule_log"] = "-"
        item["aarch64_start_time"] = "-"
        item["aarch64_end_name"] = "-"
        item["aarch64_test_duration"] = "-"

        item["x86_64_res_status"] = "-"
        item["x86_64_res_log"] = "-"
        item["x86_64_failedmodule_name"] = "-"
        item["x86_64_failedmodule_log"] = "-"
        item["x86_64_start_time"] = "-"
        item["x86_64_end_name"] = "-"
        item["x86_64_test_duration"] = "-"

        res_selectors = result.xpath('./td[starts-with(@id, "res_dvd_")]|./td[text()="-"]')
        if not res_selectors:
            test_overview_data = OpenqaTestsOverviewItem(**item)
            _redis_pipeline.process_item(test_overview_data)
            continue

        aarch64_selector = res_selectors[0]
        tmp = etree.tostring(aarch64_selector, encoding="unicode", method="xml")
        if tmp.strip() != "<td>-</td>":
            aarch64_res = aarch64_selector.xpath('./span[starts-with(@id, "res-")]/a')
            if not aarch64_res:
                res = aarch64_selector.xpath('./a')[0]
            else:
                res = aarch64_res[0]

            item["aarch64_res_status"] = res.xpath('./i/@title')[0]
            aarch64_res_log = res.xpath('./@href')[0]
            item["aarch64_res_log"] = f"{celeryconfig.openqa_url}{aarch64_res_log}"

            if item["aarch64_res_status"] != "cancelled":
                item["aarch64_start_time"], item["aarch64_end_name"], item["aarch64_test_duration"] = \
                    get_test_time_by_res_log(aarch64_res_log)

            aarch64_failedmodule = aarch64_selector.xpath('./span[@class="failedmodule"]')
            if aarch64_failedmodule:
                failedmodule = aarch64_failedmodule[0]
                item["aarch64_failedmodule_name"] = failedmodule.xpath('./a/span/text()')[0]
                item["aarch64_failedmodule_log"] = f"{celeryconfig.openqa_url}{failedmodule.xpath('./a/@href')[0]}"

        try:
            x86_64_selector = res_selectors[1]
        except IndexError:
            test_overview_data = OpenqaTestsOverviewItem(**item)
            _redis_pipeline.process_item(test_overview_data)
            continue

        tmp = etree.tostring(x86_64_selector, encoding="unicode", method="xml")
        if tmp.strip() != "<td>-</td>":
            x86_res = x86_64_selector.xpath('./span[starts-with(@id, "res-")]/a')
            if not x86_res:
                res = x86_64_selector.xpath('./a')[0]
            else:
                res = x86_res[0]

            item["x86_64_res_status"] = res.xpath('./i/@title')[0]
            x86_64_res_log = res.xpath('./@href')[0]
            item["x86_64_res_log"] = f"{celeryconfig.openqa_url}{x86_64_res_log}"
            if item["x86_64_res_status"] != "cancelled":
                item["x86_64_start_time"], item["x86_64_end_name"], item["x86_64_test_duration"] = \
                    get_test_time_by_res_log(x86_64_res_log)

            x86_failedmodule = x86_64_selector.xpath('./span[@class="failedmodule"]')
            if x86_failedmodule:
                failedmodule = x86_failedmodule[0]
                item["x86_64_failedmodule_name"] = failedmodule.xpath('./a/span/text()')[0]
                item["x86_64_failedmodule_log"] = f"{celeryconfig.openqa_url}{failedmodule.xpath('./a/@href')[0]}"

        test_overview_data = OpenqaTestsOverviewItem(**item)
        _redis_pipeline.process_item(test_overview_data)
