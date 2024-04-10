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

from functools import wraps
import requests

from flask import make_response, g, jsonify, current_app, request, Response


class RET(object):
    OK = "2000"
    OTHER_REQ_ERR = "3500"
    PARMA_ERR = "4000"
    VERIFY_ERR = "4001"
    # unauthorized request to api
    UNAUTHORIZE_ERR = "4020"
    # unauthorized access to workspaces
    UNAUTHORIZED_ACCESS = "4021"
    BAD_REQ_ERR = "4050"
    SERVER_ERR = "5000"
    DATA_EXIST_ERR = "5001"
    DB_ERR = "5002"
    NO_DATA_ERR = "5003"
    DB_DATA_ERR = "5004"
    FILE_ERR = '6000'
    SYS_CONF_ERR = "30007"
    WRONG_INSTALL_WAY = "30010"
    TASK_WRONG_GROUP_NAME = "60001"
    RUNTIME_ERROR = "60009"
    CASCADE_OP_ERR = "60010"
    CERTIFICATE_VERIFY_FAILED = "5009"
    SSLERROR = "5010"


def log_util(func_result):
    uri = str(request.path)
    ip = request.remote_addr
    act = str(request.method).upper()

    if (
            isinstance(func_result, Response)
            and func_result.mimetype == "application/json"
            and func_result.status_code == 200
    ):
        result = func_result.get_json()
        error_code = result.get("error_code")
        error_msg = result.get("error_msg")
        if error_code != RET.OK and not error_msg:
            msg = "something operate failed"
        elif error_code == RET.OK and not error_msg:
            msg = "operate success"
        elif error_code != RET.OK and error_msg:
            msg = f"operate failed:{error_msg}"
        else:
            msg = f"operate success:{error_msg}"
    elif (
            isinstance(func_result, Response)
            and func_result.mimetype != "application/json"
            and func_result.status_code == 200
    ):
        msg = "export file success"
    else:
        msg = "something operate failed"
    current_app.logger.info(
        "Ip={}, UserId={}, Method={}, Uri={}, Result={}.".format(
            ip if ip else "",
            g.user_id if g.user_id else 0,
            act,
            uri,
            msg
        )
    )


def response_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_result = func(*args, **kwargs)
        log_util(func_result)
        resp = make_response(func_result)
        if hasattr(g, "token"):
            resp.headers['Authorization'] = g.token
        return resp

    return wrapper


def ssl_cert_verify_error_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resp = func(*args, **kwargs)
            return resp
        except requests.exceptions.SSLError as e:
            current_app.logger.error(str(e))
            if "SSLCertVerificationError" in str(e):
                return jsonify(
                    error_code=RET.CERTIFICATE_VERIFY_FAILED,
                    error_msg="SSLCertVerificationError, certificate verify failed.",
                )
            return jsonify(
                error_code=RET.SSLERROR,
                error_msg="SSLError, please check your certificate.",
            )

    return wrapper


def value_error_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resp = func(*args, **kwargs)
            return resp
        except (RuntimeError, ValueError, TypeError) as e:
            current_app.logger.error(f'value_error_collect:{e}')
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e)
            )

    return wrapper


def workspace_error_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resp = func(*args, **kwargs)
            return resp
        except ValueError as e:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg=str(e),
            )
        except RuntimeError as e:
            return jsonify(
                error_code=RET.UNAUTHORIZED_ACCESS,
                error_msg=str(e),
            )

    return wrapper
