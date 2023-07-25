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

from configparser import NoOptionError, NoSectionError, ConfigParser
from pathlib import Path

from kombu import Exchange, Queue

ini_path = "/etc/radiaTest/server.ini"


def loads_config_ini(section, option):
    config_ini = Path(ini_path)

    cfg = ConfigParser()
    cfg.read(config_ini)

    try:
        return cfg.get(section, option)
    except (NoSectionError, NoOptionError):
        return None


# Broker settings
broker_url = loads_config_ini("celery", "BROKER_URL")
broker_pool_limit = 10

imports = ("manage",)

worker_state_db = "celeryservice/celerymain/celery_revokes_state_db"

# Task结果储存配置
task_ignore_result = False

# Using redis to store state and results
result_backend = loads_config_ini("celery", "RESULT_BACKEND")

# Using redis to store data of spiders
scrapyspider_backend = loads_config_ini("celery", "SCRAPYSPIDER_BACKEND")

# socketio pubsub redis url
socketio_pubsub = loads_config_ini("celery", "SOCKETIO_PUBSUB")

# 频次限制配置
worker_disable_rate_limits = True
# task_default_rate_limit = '10000/m' (10000 times per minute)

# 一般配置
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Asia/Shanghai"
enable_utc = True
# task_compression = 'gzip'

# 默认log配置
celeryd_log_file = "celeryservice/celerymain/celery.log"

# beat配置
beat_max_loop_interval = 3600

# rabbitMQ routing配置
# 队列属性定义
task_queues = (
    Queue(
        "queue_read_openqa_homepage",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="read_openqa_homepage",
    ),
    Queue(
        "queue_read_openqa_group_overview",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="read_openqa_group_overview",
    ),
    Queue(
        "queue_read_openqa_tests_overview",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="read_openqa_tests_overview",
    ),
    Queue(
        "queue_update_celerytask_status",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="celerytask_status",
    ),
    Queue(
        "queue_check_vmachine_lifecycle",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="vmachine_lifecycle",
    ),
    Queue(
        "queue_update_all_issue_rate",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="update_all_issue_rate",
    ),
    Queue(
        "queue_update_issue_type_state",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="update_issue_type_state",
    ),
    Queue(
        "queue_read_git_repo",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="git_repo",
    ),
    Queue(
        "queue_load_scripts",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="load_scripts",
    ),
    Queue(
        "queue_update_suite",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="suite",
    ),
    Queue(
        "queue_update_case",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="case",
    ),
    Queue(
        "queue_file_resolution",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="file",
    ),
    Queue(
        "queue_set_resolution",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="set",
    ),
    Queue(
        "queue_resolve_dailybuild",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="dailybuild",
    ),
    Queue(
        "queue_resolve_rpmcheck_detail",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="rpmcheck",
    ),
    Queue(
        "queue_resolve_pkglist_after_resolve_rc_name",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="rc_name",
    ),
    Queue(
        "queue_resolve_pkglist_from_url",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="pkglist_from_url",
    ),
    Queue(
        "queue_resolve_distribute_template",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="distribute_template",
    ),
    Queue(
        "queue_resolve_create_manualjob",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="create_manualjob",
    ),
    Queue(
        "queue_resolve_base_node",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="base_node",
    ),
    Queue(
        "queue_resolve_openeuler_pkglist",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="pkglist",
    ),
    Queue(
        "queue_update_compare_result",
        exchange=Exchange("compare_result", type="direct"),
        routing_key="compare_result",
    ),
    Queue(
        "queue_update_daily_compare_result",
        exchange=Exchange("daily_compare_result", type="direct"),
        routing_key="daily_compare_result",
    ),
    Queue(
        "queue_send_vmachine_release_message",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="send_vmachine_release_message",
    ),
    Queue(
        "queue_update_samerpm_compare_result",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="samerpm_compare_result",
    ),
    Queue(
        "queue_create_case_node_multi_select",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="create_case_node",
    ),
    Queue(
        "queue_check_pmachine_lifecycle",
        exchange=Exchange("server_exchange", type="direct"),
        routing_key="pmachine_lifecycle",
    ),
    Queue(
        "queue_update_case_node",
        exchange=Exchange("server_exchage", type="direct"),
        routing_key="update_case_node",
    )
)

task_default_exchange_type = "direct"

# SSL file path(Warning: if you modify this item,
# you need to change the corresponding build and deployment files)
cacert_path = loads_config_ini("server", "CA_CERT")
openqa_url = loads_config_ini("at", "OPENQA_URL")

# mail server info(make sure net is reachable)
smtp_server = loads_config_ini("mail", "SMTP_SERVER")
smtp_port = loads_config_ini("mail", "SMTP_PORT")
from_addr = loads_config_ini("mail", "FROM_ADDR")
smtp_passwd = loads_config_ini("mail", "SMTP_PASSWD")

# access_token of radiaTest-bot(make sure gitee v5 api is reachable)
v5_access_token = loads_config_ini("token", "V5_ACCESS_TOKEN")
