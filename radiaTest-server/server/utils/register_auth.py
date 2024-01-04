#! /usr/bin/env python
# coding=utf-8
# copyright (c) [2024] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
import time
from functools import wraps

from flask import request, jsonify, current_app

from server.utils.sha256_util import Hmacsha256
from server.utils.response_util import RET


def register_required(func):
    """register_required is a request interception decorator.

    It is able to verify whether registered accounts are legal
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        req_sign = request.headers.get("sign")
        timestamp = request.headers.get("timestamp")
        if not all((req_sign, timestamp)):
            return jsonify(code=RET.UNAUTHORIZE_ERR, msg="Unauthorized")

        now_timestamp = time.time()
        diff_time = int(now_timestamp) - int(timestamp)
        if diff_time > int(current_app.config.get("TIMESTAMP_THRESHOLD")):
            return jsonify(code=RET.UNAUTHORIZE_ERR, msg="Unauthorized")

        token = current_app.config.get("ROBOT_AUTHORIZE")
        str_to_sign = "{}{}".format(token, timestamp)
        sign = Hmacsha256(current_app.config.get("ROBOT_SHA256_SECRET")).encrypt(str_to_sign)

        if req_sign != sign:
            return jsonify(code=RET.UNAUTHORIZE_ERR, msg="Unauthorized")
        return func(*args, **kwargs)

    return wrapper
