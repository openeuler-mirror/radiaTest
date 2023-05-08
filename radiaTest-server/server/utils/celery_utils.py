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
            'celeryservice.tasks.async_check_vmachine_lifecycle': {
                'queue': 'queue_check_vmachine_lifecycle',
                'routing_key': 'vmachine_lifecycle',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_update_all_issue_rate': {
                'queue': 'queue_update_all_issue_rate',
                'routing_key': 'update_all_issue_rate',
                'delivery_mode': 1,
            },
            'celeryservice.lib.issuerate.update_field_issue_rate': {
                'queue': 'queue_update_field_issue_rate',
                'routing_key': 'update_field_issue_rate',
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
            'celeryservice.tasks.resolve_dailybuild_detail': {
                'queue': 'queue_resolve_dailybuild',
                'routing_key': 'set',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.resolve_rpmcheck_detail': {
                'queue': 'queue_resolve_rpmcheck_detail',
                'routing_key': 'rpmcheck',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.resolve_openeuler_pkglist': {
                'queue': 'queue_resolve_openeuler_pkglist',
                'routing_key': 'pkglist',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.resolve_pkglist_after_resolve_rc_name': {
                'queue': 'queue_resolve_pkglist_after_resolve_rc_name',
                'routing_key': 'rc_name',
                'delivery_mode': 1,
            },
            'celeryservice.sub_tasks.update_compare_result': {
                'queue': 'queue_update_compare_result',
                'routing_key': 'compare_result',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_send_vmachine_release_message': {
                'queue': 'queue_send_vmachine_release_message',
                'routing_key': 'send_vmachine_release_message',
            },
            'celeryservice.sub_tasks.update_samerpm_compare_result': {
                'queue': 'queue_update_samerpm_compare_result',
                'routing_key': 'samerpm_compare_result',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_check_pmachine_lifecycle': {
                'queue': 'queue_check_pmachine_lifecycle',
                'routing_key': 'pmachine_lifecycle',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_create_testsuite_node': {
                'queue': 'queue_update_case_node',
                'routing_key': 'update_case_node',
                'delivery_mode': 1,
            },
            'celeryservice.tasks.async_create_testcase_node': {
                'queue': 'queue_update_case_node',
                'routing_key': 'update_case_node',
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
