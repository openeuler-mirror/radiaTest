from kombu import Exchange, Queue

# TODO celery的敏感信息一样需要存入ini文件
# Broker settings
broker_url = 'amqp://radiaTest:1234@172.168.131.14:5672/radiaTest'
broker_pool_limit = 10

imports = ('tasks', )

worker_state_db = 'celeryservice/celerymain/celery_revokes_state_db'

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
    Queue(
        'queue_illegal_monitor', 
        exchange=Exchange(
            'worker#172.168.131.14_exchange', 
            type='direct'
        ),
        routing_key='illegal_monitor',
    ),
)

# worker相关配置 
# TODO 后续从ini文件读取
STORAGE_POOL = "/var/lib/libvirt/images"
NETWORK_INTERFACE_SOURCE = "br0"
SERVER_IP = "172.168.131.14"
SERVER_PORT = 1401
PROTOCOL = "http"
HEADERS = {"Content-Type": "application/json;charset=utf8"}