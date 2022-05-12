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

from gevent import monkey, pywsgi

monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from server.utils.celery_utils import make_celery
from server import create_app, db


my_celery = make_celery(__name__)

app = create_app(celery=my_celery)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command("db", MigrateCommand)


@manager.command
def run_gevent():

    server = pywsgi.WSGIServer(
        (app.config.get("SERVER_IP"), int(app.config.get("SERVER_PORT"))),
        app,
        handler_class=WebSocketHandler,
    )
    server.serve_forever()

@manager.command
def init_asr():
    from server.utils.read_from_yaml import init_role, init_scope, init_admin
    init_admin(db, app)
    init_scope(db, app)
    init_role(db, app)


if __name__ == "__main__":
    manager.run()
