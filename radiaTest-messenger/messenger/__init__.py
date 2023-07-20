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
import logging

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from importlib import import_module
from messenger.utils.config_util import loads_config_ini
from messenger.utils.celery_utils import init_celery


socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode="gevent",
)


from messenger.sockets.monitor_socket import RemoteMonitorSocket
from messenger.utils.resource_monitor import RemoteShellMonitor
from messenger.utils.resource_monitor import RemoteRestfulMonitor

socketio.on_namespace(
    RemoteMonitorSocket(
        "/monitor/normal", 
        RemoteShellMonitor
    )
)
socketio.on_namespace(
    RemoteMonitorSocket(
        "/monitor/host", 
        RemoteRestfulMonitor
    )
)


def create_app(**kwargs):
    app = Flask(__name__)

    app.config.from_object("messenger.config.settings.Config")

    ini_result = loads_config_ini(app)
    if not ini_result:
        raise RuntimeError("There is no valid config files for this flask app.")

    logging.basicConfig(
        level=app.config.get("LOG_LEVEL"),
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    )

    if kwargs.get('celery'):
        init_celery(kwargs['celery'], app)

    CORS(cors_allowed_origins="*")

    socketio.init_app(app)

    # apps
    apps = import_module('messenger.apps')
    apps.init_api(app)

    return app
