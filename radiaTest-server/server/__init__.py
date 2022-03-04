import logging

import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO
import casbin_sqlalchemy_adapter

from .utils.redis_util import RedisClient
from importlib import import_module
from .plugins.flask_authz import CasbinEnforcer
from server.utils.config_util import loads_config_ini, loads_db_url
from server.utils.celery_utils import init_celery


db = SQLAlchemy()
redis_client = RedisClient()
socketio = SocketIO(cors_allowed_origins="*", async_mode="gevent")
adapter = casbin_sqlalchemy_adapter.Adapter(
    loads_db_url("/etc/radiaTest/server.ini")
)
casbin_enforcer = CasbinEnforcer(adapter=adapter)


from server.sockets.monitor_socket import RemoteMonitorSocket
from server.utils.resource_monitor import RemoteShellMonitor, RemoteRestfulMonitor


socketio.on_namespace(
    RemoteMonitorSocket("/monitor/normal", RemoteShellMonitor)
)
socketio.on_namespace(
    RemoteMonitorSocket("/monitor/host", RemoteRestfulMonitor)
)


def create_app(**kwargs):
    app = Flask(__name__)

    app.config.from_object("server.config.settings.Config")

    ini_result = loads_config_ini(app)
    if not ini_result:
        raise RuntimeError("There is no valid config files for this flask app.")

    logging.basicConfig(
        # filename=app.config.get("LOG_PATH"),
        level=app.config.get("LOG_LEVEL"),
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    )

    if kwargs.get('celery'):
        init_celery(kwargs['celery'], app)

    CORS(cors_allowed_origins="*")
    socketio.init_app(app)

    pymysql.install_as_MySQLdb()
    db.init_app(app)

    # redis
    redis_client.init_app(app)

    # auth
    auth_util = import_module('server.utils.auth_util')
    auth_util.init(app)

    # casbin
    casbin_enforcer.init_app(app)

    # apps
    apps = import_module('server.apps')
    apps.init_api(app)

    return app
