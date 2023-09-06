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

from flask_script import Manager

from worker import create_app


app = create_app()

manager = Manager(app)

@manager.command
def run_gevent():
    server = pywsgi.WSGIServer(
        (app.config.get("WORKER_IP"), app.config.get("WORKER_PORT")), app
    )
    server.serve_forever()


if __name__ == "__main__":
    manager.run()
