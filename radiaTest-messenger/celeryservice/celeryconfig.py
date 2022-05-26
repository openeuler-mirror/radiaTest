import configparser
from pathlib import Path

from kombu import Exchange, Queue

ini_path = "/etc/radiaTest/messenger.ini"

def loads_config_ini(section, option):
    config_ini = Path(ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    if not cfg.get(section, option):
        return None

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
        'queue_run_suite',
        exchange=Exchange(
            'messenger_exchange',
            type='direct'
        ),
        routing_key='run_suite',
    ),
    Queue(
        'queue_run_template',
        exchange=Exchange(
            'messenger_exchange',
            type='direct'
        ),
        routing_key='run_template',
    ),
    Queue(
        'queue_run_case',
        exchange=Exchange(
            'messenger_exchange',
            type='direct'
        ),
        routing_key='run_case',
    ),
    Queue(
        'queue_job_callback',
        exchange=Exchange(
            'messenger_exchange',
            type='direct'
        ),
        routing_key='job_callback',
    ),
    Queue(
        'queue_check_alive',
        exchange=Exchange(
            'messenger_exchange',
            type='direct'
        ),
        routing_key='check_alive',
    ),
)

task_default_exchange_type = 'direct'

# server confg
server_addr = loads_config_ini("server", "SERVER_ADDR")

# messenger config
messenger_ip = loads_config_ini("messenger", "MESSENGER_IP")
messenger_listen = loads_config_ini("messenger", "MESSENGER_LISTEN")
protocol = loads_config_ini("messenger", "PROTOCOL")
protocol_to_server = loads_config_ini("messenger", "PROTOCOL_TO_SERVER")

# pxe config
pxe_ip = loads_config_ini("pxe", "PXE_IP")
pxe_ssh_user = loads_config_ini("pxe", "PXE_SSH_USER")
pxe_ssh_port = loads_config_ini("pxe", "PXE_SSH_PORT")
pxe_pkey = loads_config_ini("pxe", "PRIVATE_KEY")

# dhcp config
dhcp_ip = loads_config_ini("dhcp", "DHCP_IP")

