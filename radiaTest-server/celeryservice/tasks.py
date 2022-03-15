import os
import sys
import json

from flask_socketio import SocketIO
from celery import current_app as celery
from celery.utils.log import get_task_logger
from celery.signals import task_postrun
from celery.schedules import crontab

from server.model.framework import Framework, GitRepo
from server.model.celerytask import CeleryTask
from server.utils.db import Insert
from server import db, redis_client
from celeryservice.lib.job.handler import RunSuite, RunTemplate
from celeryservice.lib.repo.handler import RepoTaskHandler
from celeryservice.lib.monitor import LifecycleMonitor
from celeryservice.lib.testcase import TestcaseHandler


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


logger = get_task_logger('manage')
socketio = SocketIO(message_queue="redis://localhost:6379/10")


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
def run_suite(self, body, user):
    RunSuite(body, self, user, logger).run()


@celery.task(bind=True)
def run_template(self, body, user):
    RunTemplate(body, self, user, logger).run()


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
