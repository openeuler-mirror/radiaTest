import configparser
from pathlib import Path

from kombu import Exchange, Queue

ini_path = "/etc/radiaTest/server.ini"

def loads_config_ini(section, option):
    config_ini = Path(ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    return cfg.get(section, option)


# Broker settings
broker_url = loads_config_ini("celery", "BROKER_URL")
broker_pool_limit = 10

imports = ('manage', )

worker_state_db = 'celeryservice/celerymain/celery_revokes_state_db'

# Task结果储存配置
task_ignore_result = False

# Using mysql to store state and results
result_backend = loads_config_ini("celery", "RESULT_BACKEND")

# socketio pubsub redis url
socketio_pubsub = loads_config_ini("celery", "SOCKETIO_PUBSUB")


# 频次限制配置
worker_disable_rate_limits = True
# task_default_rate_limit = '10000/m' (10000 times per minute)

# 一般配置
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = True
# task_compression = 'gzip'

# 默认log配置
celeryd_log_file = 'celeryservice/celerymain/celery.log'

# beat配置
beat_max_loop_interval = 3600

# rabbitMQ routing配置
# 队列属性定义
task_queues = (
    Queue(
        'queue_update_celerytask_status',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='celerytask_status',
    ),
    Queue(
        'queue_check_vmachine_lifecycle',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='vmachine_lifecycle',
    ),
    Queue(
        'queue_read_git_repo',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='git_repo',
    ),
    Queue(
        'queue_load_scripts',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='load_scripts',
    ),
    Queue(
        'queue_update_suite',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='suite',
    ),
    Queue(
        'queue_update_case',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='case',
    ),
    Queue(
        'queue_run_suite',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='run_suite',
    ),
    Queue(
        'queue_run_template',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='run_template',
    ),
    Queue(
        'queue_run_case',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='run_case',
    ),
    Queue(
        'queue_job_callback',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='job_callback',
    ),
    Queue(
        'queue_file_resolution',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='file',
    ),
    Queue(
        'queue_set_resolution',
        exchange=Exchange(
            'server_exchange',
            type='direct'
        ),
        routing_key='set',
    ),
)

task_default_exchange_type = 'direct'

