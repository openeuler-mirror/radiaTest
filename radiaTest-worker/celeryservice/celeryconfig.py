# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/05
# @License : Mulan PSL v2
#####################################

import configparser
from pathlib import Path

from kombu import Exchange, Queue

celery_ini_path = "/etc/radiaTest/worker.ini"


def loads_config_ini(section, option):
    config_ini = Path(celery_ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    try:
        return cfg.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None


# Broker settings
broker_url = loads_config_ini("celery", "BROKER_URL")
broker_pool_limit = 10

imports = ('tasks',)

worker_state_db = 'celeryservice/celerymain/celery_revokes_state_db'

# Task结果储存配置
task_ignore_result = True

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

# rabbitMQ routing配置
# 队列属性定义
task_queues = (
    Queue(
        'queue_create_vmachine',
        exchange=Exchange(
            'worker_exchange',
            type='direct'
        ),
        routing_key='create_vmachine',
    ),
    Queue(
        'queue_illegal_monitor',
        exchange=Exchange(
            'worker_exchange',
            type='direct'
        ),
        routing_key='illegal_monitor',
    ),
    Queue(
        'queue_vmachines_status_monitor',
        exchange=Exchange(
            'worker_exchange',
            type='direct'
        ),
        routing_key='vmachines_status_monitor',
    ),
)

# worker相关配置 
storage_pool = loads_config_ini("worker", "STORAGE_POOL")
network_interface_source = loads_config_ini(
    "worker",
    "NETWORK_INTERFACE_SOURCE"
)

server_addr = loads_config_ini("server", "SERVER_ADDR")
# SSL file path(Warning: if you modify this item,
# you need to change the corresponding build and deployment files)
ca_verify = loads_config_ini("server", "CA_VERIFY")
cacert_path = loads_config_ini("server", "CA_CERT")

messenger_ip = loads_config_ini("messenger", "MESSENGER_IP")
messenger_listen = loads_config_ini("messenger", "MESSENGER_LISTEN")

headers = {"Content-Type": "application/json;charset=utf8"}
vmstatus_state = ("_STARTING", "_SUCCESS")
cdromstatus_state = ("CREATING", "CDROMMING", "INSTALLING", "SUCCESS")
wait_vm_shutdown = 20
wait_vm_install = 6000

# 本地源配置
disk_cache_on = loads_config_ini("worker", "DISK_CACHE_ON")
local_source_storage_pool = loads_config_ini("worker", "LOCAL_SOURCE_STORAGE_POOL")
