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
            'celeryservice.tasks.async_read_openqa_homepage': {
                'queue': 'queue_read_openqa_homepage',
                'routing_key': 'read_openqa_homepage',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.read_openqa_group_overview': {
                'queue': 'queue_read_openqa_group_overview',
                'routing_key': 'read_openqa_group_overview',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.read_openqa_tests_overview': {
                'queue': 'queue_read_openqa_tests_overview',
                'routing_key': 'read_openqa_tests_overview',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_update_celerytask_status': {
                'queue': 'queue_update_celerytask_status',
                'routing_key': 'celerytask_status',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_check_machine_lifecycle': {
                'queue': 'queue_check_machine_lifecycle',
                'routing_key': 'machine_lifecycle',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_update_issue_rate': {
                'queue': 'queue_update_issue_rate',
                'routing_key': 'update_issue_rate',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_update_issue_type_state': {
                'queue': 'queue_update_issue_type_state',
                'routing_key': 'update_issue_type_state',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_read_git_repo': {
                'queue': 'queue_read_git_repo',
                'routing_key': 'git_repo',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.load_scripts': {
                'queue': 'queue_load_scripts',
                'routing_key': 'load_scripts',
                'delivery_mode': 1,
            },
            'celeryservice.sub_tasks.update_suite': {
                'queue': 'queue_update_suite',
                'routing_key': 'suite',
                'delivery_mode': 1,
            },
            'celeryservice.sub_tasks.update_case': {
                'queue': 'queue_update_case',
                'routing_key': 'case',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.resolve_testcase_file': {
                'queue': 'queue_file_resolution',
                'routing_key': 'file',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.resolve_testcase_set': {
                'queue': 'queue_set_resolution',
                'routing_key': 'set',
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
