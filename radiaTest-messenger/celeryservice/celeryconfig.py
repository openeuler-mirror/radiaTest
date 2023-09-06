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

import configparser
from pathlib import Path

from kombu import Exchange, Queue


ini_path = "/etc/radiaTest/messenger.ini"


def loads_config_ini(section, option):
    config_ini = Path(ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    try:
        return cfg.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None


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
        routing_key='async_check_alive',
    ),
)

task_default_exchange_type = 'direct'

# server confg
server_addr = loads_config_ini("server", "SERVER_ADDR")
ca_verify = loads_config_ini("server", "CA_VERIFY")
# SSL file path(Warning: if you modify this item,
# you need to change the corresponding build and deployment files)
cacert_path = loads_config_ini("server", "CA_CERT")

# messenger config
messenger_ip = loads_config_ini("messenger", "MESSENGER_IP")
messenger_listen = loads_config_ini("messenger", "MESSENGER_LISTEN")

# pxe config
pxe_ip = loads_config_ini("pxe", "PXE_IP")
pxe_ssh_user = loads_config_ini("pxe", "PXE_SSH_USER")
pxe_ssh_port = loads_config_ini("pxe", "PXE_SSH_PORT")
pxe_pkey = loads_config_ini("pxe", "PRIVATE_KEY")

# dhcp config
dhcp_ip = loads_config_ini("dhcp", "DHCP_IP")

#at config
iso_local_path = loads_config_ini("at", "ISO_LOCAL_PATH")
iso_web_addr = loads_config_ini("at", "ISO_WEB_ADDR")
source_iso_addr = loads_config_ini("at", "SOURCE_ISO_ADDR")
mugen_path_docker = loads_config_ini("at", "MUGEN_PATH_DOCKER")
mugen_path_stra = loads_config_ini("at", "MUGEN_PATH_STRA")
at_iso_dir = loads_config_ini("at", "AT_ISO_DIR")
at_qcow2_dir = loads_config_ini("at", "AT_QCOW2_DIR")
api_key = loads_config_ini("at", "API_KEY")
api_secret = loads_config_ini("at", "API_SECRET")
at_post_url = loads_config_ini("at", "AT_POST_URL")
at_get_url = loads_config_ini("at", "AT_GET_URL")
waiting_time = 60
openqa_port = loads_config_ini("at", "OPENQA_PORT")
local_hdd = loads_config_ini("at", "LOCAL_HDD")
