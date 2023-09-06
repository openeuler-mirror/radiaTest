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

from celery import Celery
from celeryservice import celeryconfig


def make_celery(app_name):
    broker = celeryconfig.broker_url
    backend = celeryconfig.result_backend

    celery = Celery(
        app_name,
        broker=broker,
        backend=backend,
        task_routes={
            'celeryservice.tasks.run_suite': {
                'queue': 'queue_run_suite',
                'routing_key': 'run_suite',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.run_template': {
                'queue': 'queue_run_template',
                'routing_key': 'run_template',
                'delivery_mode': 1,
            },
            'celeryservice.sub_tasks.job_result_callback': {
                'queue': 'queue_job_callback',
                'routing_key': 'job_callback',
                'delivery_mode': 1,
            },
            'celeryservice.sub_tasks.run_case': {
                'queue': 'queue_run_case',
                'routing_key': 'run_case',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_check_alive': {
                'queue': 'queue_check_alive',
                'routing_key': 'check_alive',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.run_at': {
                'queue': 'queue_run_at',
                'routing_key': 'run_at',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.run_pxe_install': {
                'queue': 'queue_run_pxe_install',
                'routing_key': 'run_pxe_install',
                'delivery_mode': 1,
            },
        }
    )

    return celery


def init_celery(celery, app):
    """
    initial celery object wraps the task execution in an application context
    """
    celery.config_from_object(celeryconfig)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwds):
            with app.app_context():
                return self.run(*args, **kwds)

    celery.Task = ContextTask
