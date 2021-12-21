# @Author : lemon-higgins
# @Date   : 2021-09-19 14:54:44
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Desc   :

import logging

import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .utils.redis_util import RedisClient
from importlib import import_module

from flask_cors import CORS
from flask_socketio import SocketIO


db = SQLAlchemy()
redis_client = RedisClient()
socketio = SocketIO(cors_allowed_origins="*", async_mode="gevent")

from server.sockets.monitor_socket import RemoteMonitorSocket
from server.utils.resource_monitor import RemoteShellMonitor, RemoteRestfulMonitor

socketio.on_namespace(
    RemoteMonitorSocket("/monitor/normal", RemoteShellMonitor)
)
socketio.on_namespace(
    RemoteMonitorSocket("/monitor/host", RemoteRestfulMonitor)
)

def create_app():
    app = Flask(__name__)

    app.config.from_object("server.config.settings.Config")
    # app.config.from_object("server.config.settings.DevelopmentConfig")
    # app.config.from_object("server.config.settings.ProductionConfig")

    logging.basicConfig(
        # filename=app.config.get("LOG_PATH"),
        level=app.config.get("LOG_LEVEL"),
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    )

    CORS(cors_allowed_origins="*")
    socketio.init_app(app)

    pymysql.install_as_MySQLdb()
    db.init_app(app)

    # redis
    redis_client.init_app(app)

    # auth
    auth_util = import_module('server.utils.auth_util')
    auth_util.init(app)

    # apps
    apps = import_module('server.apps')
    apps.init_api(app)

    return app
