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

import redis
from flask_socketio import SocketIO
from celery import current_app as celery
from celery.utils.log import get_task_logger
from celery.signals import task_postrun
from celery.schedules import crontab

from server.model.framework import Framework, GitRepo
from server.model.celerytask import CeleryTask
from server.utils.db import Insert
from server.utils.shell import add_escape
from server import db
from celeryservice import celeryconfig
from celeryservice.lib.repo.handler import RepoTaskHandler
from celeryservice.lib.monitor import LifecycleMonitor, UpdateIssueRate, UpdateIssueTypeState
from celeryservice.lib.testcase import TestcaseHandler


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
        async_check_machine_lifecycle.s(),
        name="check_machine_lifecycle",
    )
    sender.add_periodic_task(
        crontab(minute="*/60"), async_read_git_repo.s(), name="read_git_repo"
    )
    sender.add_periodic_task(
        crontab(minute="*/30"), async_update_issue_rate.s(), name="update_issue_rate"
    )
	sender.add_periodic_task(
        crontab(minute=0, hour=0, day_of_month="15,30"), async_update_issue_type_state.s(), name="update_issue_type_state"
    )
    sender.add_periodic_task(
        crontab(minute="*/60"), async_read_openqa_homepage.s(), name="read_openqa"
    )


@celery.task
def async_read_openqa_homepage():
    exitcode, output = subprocess.getstatusoutput(
        f"pushd scrapyspider && scrapy crawl openqa_home_spider -a openqa_url={celeryconfig.openqa_url}"
    )
    if exitcode != 0:
        logger.error(f"crawl data from openQA homepage fail. Because {output}")

    redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
    _keys = redis_client.keys("*_group_overview_url")
    
    if not _keys:
        logger.warning("No products on openQA homepage, or the openQA server met some problems")
        return

    logger.info("crawl data from openQA homepage succeed")

    for _key in _keys:
        group_overview_url = redis_client.get(_key)
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

    redis_client = redis.StrictRedis(connection_pool=scrapyspider_pool)
    _keys = redis_client.keys(f"{product_name}_*_tests_overview_url")
    for _key in _keys:
        tests_overview_url = redis_client.get(_key)
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
    redis_client = redis.StrictRedis(connection_pool=pool)

    # 查询数据库持久化存储的celery task
    _tasks = CeleryTask.query.all()

    for _task in _tasks:
        str_t = redis_client.get("celery-task-meta-{}".format(_task.tid))

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
def async_check_machine_lifecycle():
    LifecycleMonitor(logger).main()


@celery.task
def async_update_issue_rate():
    UpdateIssueRate(logger).main()


@celery.task(bind=True)
def load_scripts(self, id, name, url, template_name):
    RepoTaskHandler(logger, self).main(id, name, url, template_name)


@celery.task
def async_read_git_repo():
    frameworks = Framework.query.filter_by(adaptive=True).all()

    for framework in frameworks:
        if framework.adaptive is True:
            repos = GitRepo.query.filter_by(
                framework_id=framework.id,
                sync_rule=True,
            ).all()

            for repo in repos:
                _task = load_scripts.delay(
                    repo.id,
                    repo.name,
                    repo.git_url,
                    framework.name,
                )

                logger.info(f"task id: {_task.task_id}")

                celerytask = {
                    "tid": _task.task_id,
                    "status": "PENDING",
                    "object_type": "scripts_load",
                    "description": f"from {repo.git_url}",
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
def async_update_issue_type_state():
    UpdateIssueTypeState(logger).main()
