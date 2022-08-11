import os
import json
import logging
import logging.config
from celery import current_app

import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO

from .utils.redis_util import RedisClient
from importlib import import_module
from .plugins.flask_authz import CasbinEnforcer
from server.utils.config_util import loads_config_ini
from server.utils.celery_utils import init_celery


db = SQLAlchemy()
redis_client = RedisClient()
scrapyspider_redis_client = RedisClient()
socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode="gevent",
)
casbin_enforcer = CasbinEnforcer()


def init_logging(default_level, cfg_path):
    if os.path.exists(cfg_path):
        with open(cfg_path, 'rt') as file:
            config = json.load(file)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=default_level,
            format="%(asctime)s, %(levelname)s - %(name)s: %(message)s",
        )


def create_app(**kwargs):
    app = Flask(__name__)

    app.config.from_object("server.config.settings.Config")

    ini_result = loads_config_ini(app)
    if not ini_result:
        raise RuntimeError("There is no valid config files for this flask app.")

    init_logging(
        default_level=app.config.get("LOG_LEVEL", logging.INFO),
        cfg_path=app.config.get("LOG_CONF", 'server/config/logging.json')
    )

    if kwargs.get('celery'):
        init_celery(kwargs['celery'], app)

    CORS(cors_allowed_origins="*")

    socketio.init_app(
        app, message_queue=app.config.get("SOCKETIO_PUBSUB")
    )

    pymysql.install_as_MySQLdb()
    db.init_app(app)

    # redis
    redis_client.init_app(app)
    app.config["REDIS_DB"] = app.config.get("REDIS_SCRAPYSPIDER_DB")
    scrapyspider_redis_client.init_app(app)

    # auth
    auth_util = import_module('server.utils.auth_util')
    auth_util.init(app)

    # casbin
    from .plugins.casbin_sqlalchemy_adapter import Adapter
    adapter = Adapter(
        app.config.get("SQLALCHEMY_DATABASE_URI")
    )
    casbin_enforcer.init_app(app, adapter)

    # apps
    apps = import_module('server.apps')
    apps.init_api(app)

    return app
