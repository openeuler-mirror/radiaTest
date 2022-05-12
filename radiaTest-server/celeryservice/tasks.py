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
from server import db
from celeryservice import celeryconfig
from celeryservice.lib.repo.handler import RepoTaskHandler
from celeryservice.lib.monitor import LifecycleMonitor
from celeryservice.lib.testcase import TestcaseHandler


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


logger = get_task_logger('manage')
socketio = SocketIO(message_queue=celeryconfig.socketio_pubsub)

# 建立redis backend连接池子
pool = redis.ConnectionPool.from_url(
    celeryconfig.result_backend, 
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
        crontab(minute='*/30'), async_check_vmachine_lifecycle.s(), name="check_vmachine_lifecycle"
    )
    sender.add_periodic_task(
        crontab(minute='*/60'), async_read_git_repo.s(), name="read_git_repo"
    )


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
def async_check_vmachine_lifecycle():
    LifecycleMonitor(logger).main()


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

                _ = Insert(CeleryTask, celerytask).single(
                    CeleryTask, '/celerytask')


@celery.task(bind=True)
def resolve_testcase_file(self, filepath, user):
    TestcaseHandler(user, logger, self).resolve(
        filepath,
    )


@celery.task(bind=True)
def resolve_testcase_file_for_baseline(self, file_id, filepath, user):
    TestcaseHandler(user, logger, self).resolve(
        filepath,
        file_id,
    )


@celery.task(bind=True)
def resolve_testcase_set(self, zip_filepath, unzip_filepath, user):
    TestcaseHandler(user, logger, self).resolve_case_set(
        zip_filepath,
        unzip_filepath,
    )
