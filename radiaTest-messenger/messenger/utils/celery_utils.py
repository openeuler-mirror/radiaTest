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
