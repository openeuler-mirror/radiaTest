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

from flask import Flask
from flask_restful import Api

from messenger.apps import (
    job,
    pmachine,
    vmachine,
    heartbeat,
    certifi,
    at,
)


def init_api(app: Flask):
    api = Api(app)
    job.init_api(api)
    pmachine.init_api(api)
    vmachine.init_api(api)
    heartbeat.init_api(api)
    certifi.init_api(api)
    at.init_api(api)
