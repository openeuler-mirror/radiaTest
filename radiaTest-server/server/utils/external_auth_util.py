# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/20
# @License : Mulan PSL v2
#####################################
import time

from functools import wraps
from flask import jsonify, request, current_app

from server.utils.response_util import RET
from server.utils.sha256_util import Hmacsha256


def external_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            req_sign = request.headers.get("sign")
            req_ts = request.headers.get("timestamp")
            if req_sign and req_ts:
                now_timestamp = time.time()
                diff_time = int(now_timestamp) - int(req_ts)
                if diff_time <= int(current_app.config.get("TIMESTAMP_THRESHOLD")):
                    token = current_app.config.get("EXTERNAL_AUTHORIZE")
                    str_to_sign = "{}{}".format(token, req_ts)
                    sign = Hmacsha256(current_app.config.get("EXTERNAL_SHA256_SECRET")).encrypt(str_to_sign)
                    if req_sign == sign:
                        resp = func(*args, **kwargs)
                        return resp
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="unauth request"
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg=str(e)
            )
    return wrapper
