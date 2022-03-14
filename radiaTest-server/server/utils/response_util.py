from flask import make_response, g
from functools import wraps


class RET(object):
    OK = "2000"
    OTHER_REQ_ERR = "3500"
    OTHER_REQ_TIMEOUT = "3504"
    PARMA_ERR = "4000"
    VERIFY_ERR = "4001"
    CLA_VERIFY_ERR = "4010"
    UNAUTHORIZE_ERR = "4020"
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


def response_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_result = func(*args, **kwargs)
        resp = make_response(func_result)
        resp.headers['Authorization'] = g.token
        return resp

    return wrapper
