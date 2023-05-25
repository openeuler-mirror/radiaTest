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

import subprocess
import os
import sys
import json
import requests

import redis
from flask_socketio import SocketIO
from celery import current_app as celery
from celery.utils.log import get_task_logger
from celery.signals import task_postrun
from celery.schedules import crontab

from server import redis_client
from server.model.framework import GitRepo
from server.model.testcase import Suite
from server.model.celerytask import CeleryTask
from server.utils.db import Insert
from server.utils.shell import add_escape
from server import db
from celeryservice import celeryconfig
from celeryservice.lib.repo.handler import RepoTaskHandler
from celeryservice.lib.monitor import LifecycleMonitor
from celeryservice.lib.issuerate import UpdateIssueRate, UpdateIssueTypeState
from celeryservice.lib.testcase import TestcaseHandler
from celeryservice.lib.dailybuild import DailyBuildHandler
from celeryservice.lib.message import VmachineReleaseNotice
from celeryservice.lib.rpmcheck import RpmCheckHandler
from celeryservice.lib.casenode import CaseNodeCreator
from celeryservice.lib.template import TemplateCaseHandler


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


logger = get_task_logger("manage")
socketio = SocketIO(message_queue=celeryconfig.socketio_pubsub)

# 建立redis backend连接池
pool = redis.ConnectionPool.from_url(celeryconfig.result_backend, decode_responses=True)
# 建立scrapyspider的存储redis池
scrapyspider_pool = redis.ConnectionPool.from_url(celeryconfig.scrapyspider_backend, decode_responses=True)


@task_postrun.connect
def close_session(*args, **kwargs):
    db.session.remove()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0, async_update_celerytask_status.s(), name="update_celerytask_status"
    )
    sender.add_periodic_task(
        crontab(minute="*/30"),
        async_check_vmachine_lifecycle.s(),
        name="check_vmachine_lifecycle",
    )
    sender.add_periodic_task(
        crontab(minute="*/30"), async_update_all_issue_rate.s(), name="update_all_issue_rate"
    )
    sender.add_periodic_task(
        crontab(minute=0, hour=0, day_of_month="15,30"), async_update_issue_type_state.s(), name="update_issue_type_state"
    )
    sender.add_periodic_task(
        crontab(minute="*/60"), async_read_openqa_homepage.s(), name="read_openqa"
    )
    sender.add_periodic_task(
        crontab(minute="*/50"),
        async_send_vmachine_release_message.s(),
        name="send_vmachine_release_message",
    )
    sender.add_periodic_task(
        crontab(minute="*/5"),
        async_check_pmachine_lifecycle.s(),
        name="check_pmachine_lifecycle",
    )


@celery.task
def async_read_openqa_homepage():
    exitcode, output = subprocess.getstatusoutput(
        f"pushd scrapyspider && scrapy crawl openqa_home_spider -a openqa_url={celeryconfig.openqa_url}"
    )
    if exitcode != 0:
        logger.error(f"crawl data from openQA homepage fail. Because {output}")

    _redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
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
    exitcode, output = subprocess.getstatusoutput(
        "pushd scrapyspider && scrapy crawl openqa_group_overview_spider "\
            f"-a product_name={product_name} "\
            f"-a group_overview_url={celeryconfig.openqa_url}{add_escape(group_overview_url)}"
    )
    if exitcode != 0:
        logger.error(f"crawl group overview data of product {product_name} fail. Because {output}")
    
    logger.info(f"crawl group overview data of product {product_name} succeed")

    _redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
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
    exitcode, output = subprocess.getstatusoutput(
        "pushd scrapyspider && scrapy crawl openqa_tests_overview_spider "\
            f"-a product_build={product_build} "\
            f"-a openqa_url={celeryconfig.openqa_url} "\
            f"-a tests_overview_url={add_escape(tests_overview_url)}"
    )
    if exitcode != 0:
        logger.error(f"crawl tests overview data of product {product_build} fail. Because {output}")
    
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
def async_check_vmachine_lifecycle():
    LifecycleMonitor(logger).check_vmachine_lifecycle()


@celery.task
def async_update_all_issue_rate():
    UpdateIssueRate(logger).main()


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


@celery.task(bind=True)
def resolve_template_testcase(self, filetype, filepath, body):
    TemplateCaseHandler(logger, self).import_cases_to_template(
        filetype=filetype,
        filepath=filepath,
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
def resolve_openeuler_pkglist(repo_url, product, build, repo_path, arch, round=None):
    exitcode, output = subprocess.getstatusoutput(
        "pushd scrapyspider && scrapy crawl openeuler_pkgs_list_spider "\
            f"-a openeuler_repo_url={repo_url} "\
            f"-a product={product} "\
            f"-a build={build} "\
            f"-a repo_path={repo_path} "\
            f"-a arch={arch} "\
            f"-a round={round}"
    )
    if exitcode != 0:
        logger.error(f"crawl openeuler's packages list of build {build} of {product} fail. Because {output}")
        return
    
    logger.info(f"crawl openeuler's packages list of build {build} of {product} succeed")
    lock_key = f"resolving_{product}-release-{repo_path}-{arch}_pkglist"
    if product != build:
        lock_key = f"resolving_{product}-round-{round}-{repo_path.split('/')[0]}-{arch}_pkglist"
    redis_client.delete(lock_key)
    logger.info(f"the lock of crawling has been removed")


@celery.task
def resolve_pkglist_after_resolve_rc_name(repo_url, store_path, product, round_num=None):
    if not repo_url or not store_path or not  product:
        logger.error("neither param repo_url store_path product could be None.")
        return

    _repo_url = repo_url
    product_version = f"{store_path}/{product}"
    if round_num :
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
        exitcode, output = subprocess.getstatusoutput(
            f"cat {tmp_file_name} | grep 'rc{round_num}_openeuler'"
            + " | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | uniq"
        )
        if exitcode != 0:
            logger.error(output)
            return
        _repo_url = f'{_repo_url}/{output}'

    for repo_path in ["everything", "EPOL/main"]:
        product_version_repo = f"{product_version}-{repo_path.split('/')[0]}"
        for arch in ["aarch64", "x86_64"]:
            _url =  f"{_repo_url}/{repo_path}/{arch}/Packages/"
            resp = requests.get(_url)
            if resp.status_code != 200:
                logger.error("Could not connect to the url: {}".format(_url))
                return
            resp.encoding = 'utf-8'
            # 写入网页内容到文件中
            tmp_file_name = f"{product_version_repo}-{arch}-html.txt"
            with open(tmp_file_name, "wb") as f:
                f.write(resp.content)
                f.close()

            exitcode, output = subprocess.getstatusoutput(
                f"cat {tmp_file_name} | " 
                + "grep 'title=' | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | grep '.rpm' | uniq >" 
                + f"{product_version_repo}-{arch}.pkgs"
            )
            if exitcode != 0:
                logger.error(output)
                return

        exitcode, output = subprocess.getstatusoutput(
            f"sort {product_version_repo}-aarch64.pkgs"
            + f" {product_version_repo}-x86_64.pkgs | uniq >{product_version_repo}-all.pkgs"
        )
        if exitcode != 0:
            logger.error(output)
            return
    _, _ = subprocess.getstatusoutput(
        f"rm -f {store_path}/{product}*html.txt"
    )

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
            _url =  f"{repo_url}/{repo_path}/{arch}/Packages/"
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

            exitcode, output = subprocess.getstatusoutput(
                f"cat {tmp_file_name} | " 
                + "grep 'title=' | awk -F 'title=\"' '{print $2}' | awk -F '\">' '{print $1}' | grep '.rpm' | uniq >" 
                + f"{store_path}/{_repo_path}-{arch}.pkgs"
            )

            if exitcode != 0:
                logger.error(output)
                return

        exitcode, output = subprocess.getstatusoutput(
            f"sort {store_path}/{_repo_path}-aarch64.pkgs"
            + f" {store_path}/{_repo_path}-x86_64.pkgs | uniq >{store_path}/{_repo_path}-all.pkgs"
        )
        if exitcode != 0:
            logger.error(output)
            return
    _, _ = subprocess.getstatusoutput(
        f"rm -f {store_path}/{repo_name}*html.txt"
    )

    logger.info(f"crawl openeuler's packages list of {repo_name} succeed")
    lock_key = f"resolving_{repo_name}_pkglist"
    redis_client.delete(lock_key)
    logger.info(f"the lock of crawling has been removed")


@celery.task
def async_send_vmachine_release_message():
    VmachineReleaseNotice(logger).main()


@celery.task
def async_check_pmachine_lifecycle():
    LifecycleMonitor(logger).check_pmachine_lifecycle()


@celery.task(bind=True)
def async_create_testsuite_node(
    self,
    parent_id: int, # 被创建suite类型节点的父节点 
    suite_id: int, # 被创建suite类型节点关联的用例ID
    permission_type: str = 'public', # 被创建suite类型节点的权限类型 
    org_id: int = None, # 被创建suite类型节点的所属组织
    group_id: int = None, # 被创建suite类型节点的所属团队
    user_id: str = None, # 创建异步任务的当前用户id
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
    parent_id: int, # 被创建case类型节点的父节点 
    case_name: str, # 被创建case类型节点关联的用例名 
    case_id: int, # 被创建case类型节点关联的用例ID
    permission_type: str = 'public', # 被创建case类型节点的权限类型 
    org_id: int = None, # 被创建case类型节点的所属组织
    group_id: int = None, # 被创建case类型节点的所属团队 
):
    CaseNodeCreator(logger, self).create_case_node(
        parent_id,
        case_name,
        case_id,
        permission_type,
        org_id,
        group_id,
    )