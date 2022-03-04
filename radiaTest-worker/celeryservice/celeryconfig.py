# import datetime
from celery.schedules import crontab
from datetime import timedelta
from kombu import Exchange, Queue

# TODO celery的敏感信息一样需要存入ini文件
# Broker settings
broker_url = 'amqp://radiaTest:1234@172.168.131.14:5672/radiaTest'
broker_pool_limit = 10

imports = ('tasks', )

worker_state_db = 'celeryservice/celerymain.celery_revokes_state_db'

# Task结果储存配置
task_ignore_result = True

## Using mysql to store state and results
result_backend = 'redis://localhost:6379/11'

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

# 默认邮件配置
# CELERY_SEND_TASK_ERROR_EMAILS = True
# ADMINS = ("radiaTest", "email@email.com")
# SERVER_EMAIL = "email@email.com"
# EMAIL_HOST = "email.host.com"
# EMAIL_HOST_PASSWORD = "xxxxxxxx"
# EMAIL_PORT = "<int: xx>"
# EMAIL_USE_SSL = False
# EMAIL_USE_TLS = False
# EMAIL_TIMEOUT = 2 # 2s

# rabbitMQ routing配置
## 队列属性定义 后续ip使用动态获取
task_queues = (
    Queue(
        'queue_create_vmachine', 
        exchange=Exchange(
            'worker#172.168.131.14_exchange', 
            type='direct'
        ),
        routing_key='create_vmachine',
    ),
)

# TASK_DEFAULT_QUEUE = 'celery'
# TASK_DEFAULT_EXCHANGE_TYPE = 'direct'
# TASK_DEFAULT_ROUTING_KEY = 'celery'

## 路由属性配置
## delivery_mode = 1 非持久化存储Tasks信息
## delivery_mode = 2 持续化存储Tasks信息
# celery_routes = {
#     'celeryservice.tasks.create_vmachine': {
#         'queue': 'queue_create_vmachine',
#         'routing_key': 'create_vmachine',
#         'delivery_mode': 1,
#     },
# }

# worker相关配置 后续从ini文件读取
STORAGE_POOL = "/var/lib/libvirt/images"
NETWORK_INTERFACE_SOURCE = "br0"
SERVER_IP = "172.168.131.14"
SERVER_PORT = 1401
PROTOCOL = "http"
HEADERS = {"Content-Type": "application/json;charset=utf8"}