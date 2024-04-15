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
import ssl
from configparser import NoOptionError, NoSectionError, ConfigParser
from pathlib import Path

from kombu import Exchange, Queue

INI_PATH = "/etc/radiaTest/server.ini"


def loads_config_ini(section, option):
    config_ini = Path(INI_PATH)

    cfg = ConfigParser()
    cfg.read(config_ini)

    try:
        return cfg.get(section, option)
    except (NoSectionError, NoOptionError):
        return None


# Broker settings
broker_url = loads_config_ini("celery", "BROKER_URL")
broker_use_ssl = {
    'ssl_version': ssl.PROTOCOL_TLSv1_2,
    'cert_reqs': ssl.CERT_NONE,
}
broker_pool_limit = 10
imports = ("manage",)

# Using redis to store state and results
result_backend = "{}?ssl_cert_reqs=required&ssl_ca_certs=/etc/radiaTest/redis.crt".format(
    loads_config_ini("celery", "RESULT_BACKEND"))

# Using redis to store data of spiders
SCRAPYSPIDER_BACKEND = "{}?ssl_cert_reqs=required&ssl_ca_certs=/etc/radiaTest/redis.crt".format(
    loads_config_ini("celery", "SCRAPYSPIDER_BACKEND"))

# socketio pubsub redis url
SOCKETIO_PUBSUB = loads_config_ini("celery", "SOCKETIO_PUBSUB")

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
        "queue_update_case_node",
        exchange=Exchange("server_exchage", type="direct"),
        routing_key="update_case_node",
    )
)

OPENQA_URL = loads_config_ini("at", "OPENQA_URL")


# access_token of radiaTest-bot(make sure gitee v5 api is reachable)
V5_ACCESS_TOKEN = loads_config_ini("token", "V5_ACCESS_TOKEN")

