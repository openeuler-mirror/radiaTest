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

import requests

from flask import make_response, g, jsonify, current_app
from functools import wraps


class RET(object):
    OK = "2000"
    OTHER_REQ_ERR = "3500"
    OTHER_REQ_TIMEOUT = "3504"
    PARMA_ERR = "4000"
    VERIFY_ERR = "4001"
    CLA_VERIFY_ERR = "4010"
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
    DATA_DEL_ERR = "30006"
    SYS_CONF_ERR = "30007"
    WRONG_INSTALL_WAY = "30010"
    INSTALL_CONF_ERR = "50008"
    NET_CONF_ERR = "50009"
    NET_CONECT_ERR = "50010"
    NO_MEM_ERR = "50011"
    TASK_WRONG_GROUP_NAME = "60001"
    WRONG_REPO_URL = "60002"
    RUNTIME_ERROR = "60009"
    CASCADE_OP_ERR = "60010"
    CERTIFICATE_VERIFY_FAILED = "5009"
    SSLERROR = "5010"
    MAIL_ERROR = "80000"


def response_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_result = func(*args, **kwargs)
        resp = make_response(func_result)
        resp.headers['Authorization'] = g.token
        return resp

    return wrapper


def attribute_error_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            resp = func(*args, **kwargs)
            return resp
        except AttributeError as e:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg=str(e)
            )

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
                return dict(
                    error_code=RET.CERTIFICATE_VERIFY_FAILED,
                    error_msg="SSLCertVerificationError, certificate verify failed.",
                )
            return dict(
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


def  workspace_error_collect(func):
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