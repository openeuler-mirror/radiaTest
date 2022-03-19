import configparser
from pathlib import Path
import socket

from kombu import Exchange, Queue

celery_ini_path = "/etc/radiaTest/worker.ini"

def loads_config_ini(section, option):
    config_ini = Path(celery_ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    return cfg.get(section, option)
 
def get_current_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
 
    return ip


# Broker settings
broker_url = loads_config_ini("celery","BROKER_URL")
broker_pool_limit = 10

imports = ('tasks', )

worker_state_db = 'celeryservice/celerymain/celery_revokes_state_db'

# Task结果储存配置
task_ignore_result = True

## Using mysql to store state and results
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

# rabbitMQ routing配置
## 队列属性定义
task_queues = (
    Queue(
        'queue_create_vmachine', 
        exchange=Exchange(
            'worker@{}_exchange'.format(
                get_current_ip()
            ),
            type='direct'
        ),
        routing_key='create_vmachine',
    ),
    Queue(
        'queue_illegal_monitor', 
        exchange=Exchange(
            'worker@{}_exchange'.format(
                get_current_ip()
            ),
            type='direct'
        ),
        routing_key='illegal_monitor',
    ),
)

# worker相关配置 
STORAGE_POOL = loads_config_ini("worker","STORAGE_POOL")
NETWORK_AUTHENTICATION_REQUIRED = loads_config_ini(
    "worker",
    "NETWORK_AUTHENTICATION_REQUIRED"
)
SERVER_IP = loads_config_ini("worker","SERVER_IP")
SERVER_PORT = loads_config_ini("worker","SERVER_PORT")
PROTOCOL = loads_config_ini("worker","PROTOCOL")
HEADER = loads_config_ini("worker","HEADER")
