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
from flask_migrate import Migrate, MigrateCommand

from server.utils.celery_utils import make_celery
from server import create_app, db, redis_client, swagger_adapt

my_celery = make_celery(__name__)

app = create_app(celery=my_celery)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

migrate = Migrate(app, db)

app.cli.add_command("db", MigrateCommand)


@app.cli.command("run_gevent")
def run_gevent():

    server = pywsgi.WSGIServer(
        (
            app.config.get("SERVER_IP"),
            app.config.get("SERVER_PORT"),
        ),
        app,
        handler_class=WebSocketHandler
    )
    server.serve_forever()


@app.cli.command("init_asr")
def init_asr():
    from server.utils.read_from_yaml import init_role, init_scope, init_admin
    from server.utils.public_login_util import init_public_login
    init_admin(db, app)
    init_scope(db, app)
    init_role(db, app)
    init_public_login(app, redis_client)


@app.cli.command("prepare_recv_id")
def prepare_recv_id():
    from server.utils.read_from_yaml import get_recv_id
    get_recv_id(db, app)


@app.cli.command("swagger_init")
def swagger_init():
    # 批量添加路由地址和请求方式
    api_info_map = swagger_adapt.api_info_map
    for rule in app.url_map.iter_rules():
        methods = rule.methods
        url = rule.rule
        # 忽略静态资源路径
        if url.startswith("/static"):
            continue
        for method in methods:
            method = method.lower()
            # 忽略部分请求方式
            if method in ["head", "options"]:
                continue
            view_func = app.view_functions.get(rule.endpoint)
            if view_func:
                if not hasattr(view_func, "view_class"):
                    continue
                __module__ = view_func.view_class.__module__
                if __module__ in api_info_map:
                    resource_name = view_func.view_class.__name__
                    if resource_name in api_info_map[__module__]:
                        if method in api_info_map[__module__][resource_name]:
                            # 接口存在多路径
                            if "url" in api_info_map[__module__][resource_name][method]:
                                api_info_map[__module__][resource_name][method]["url"].append(url)
                            else:
                                api_info_map[__module__][resource_name][method].update({
                                    "url": [url],
                                    "method": method,
                                })

    # 保存api map信息
    swagger_adapt.save_api_info_map()


if __name__ == "__main__":
    app.run()
