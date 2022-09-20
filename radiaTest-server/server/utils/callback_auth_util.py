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

from flask import jsonify, request, g
from functools import wraps

from server import redis_client
from server.utils.response_util import RET


def callback_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            req_auth = request.headers.get("authorization")
            g.token = req_auth
            _body = request.get_json()
            vm_name = _body.pop("name")
            origin_auth = redis_client.get(vm_name)
            if origin_auth is None or origin_auth != req_auth:
                raise RuntimeError("request source is unauthorized")
            redis_client.delete(vm_name)
            resp = func(*args, **kwargs)
            return resp
        except RuntimeError as e:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg=str(e)
            )
    return wrapper
