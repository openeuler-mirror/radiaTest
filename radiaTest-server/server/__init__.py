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

import os
import json
import logging
import logging.config
from pathlib import Path

import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_swagger_ui import get_swaggerui_blueprint


from .utils.redis_util import RedisClient
from importlib import import_module
from .plugins.flask_authz import CasbinEnforcer
from server.config.settings import Config
from server.utils.config_util import loads_config_ini
from server.utils.celery_utils import init_celery
from server.plugins.swagger.adapt_swagger import SwaggerJsonAdapt


db = SQLAlchemy()
redis_client = RedisClient()
socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode="gevent",
)
casbin_enforcer = CasbinEnforcer()

# swagger
swagger_url = Config.SWAGGER_URL  # nginx代理原因, 必须以/static路径开头才能访问
api_url = Config.SWAGGER_YAML_FILE  # 实际api文件, 将文件放入{SWAGGER_URL}/dist/
swagger_blueprint = get_swaggerui_blueprint(
    swagger_url,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    api_url,
    config={  # Swagger UI config overrides
        'app_name': "api docs application"
    }
)
Path(swagger_blueprint.static_folder)
swagger_adapt = SwaggerJsonAdapt(Path(swagger_blueprint.static_folder).joinpath(api_url))


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

    # auth
    auth_util = import_module('server.utils.auth_util')
    auth_util.init(app)

    # casbin
    from .plugins.casbin_sqlalchemy_adapter import Adapter
    adapter = Adapter(filtered=True)
    
    casbin_enforcer.init_app(app, adapter)

    # 生产环境默认关闭swagger
    swagger_switch = Config.SWAGGER_SWITCH
    if isinstance(swagger_switch, str) and swagger_switch.lower() == "on":
        app.register_blueprint(swagger_blueprint, url_prefix=swagger_url)

    # apps
    apps = import_module('server.apps')
    apps.init_api(app)

    return app
