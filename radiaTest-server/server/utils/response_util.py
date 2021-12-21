from flask import make_response, g
from functools import wraps


class RET(object):
    OK = "2000"
    PARMA_ERR = "4000"
    VERIFY_ERR = "4001"
    CLA_VERIFY_ERR = "4010"
    OTHER_REQ_ERR = "3500"
    OTHER_REQ_TIMEOUT = "3504"
    SERVER_ERR = "5000"
    DATA_EXIST_ERR = "5001"
    DB_ERR = "5002"
    NO_DATA_ERR = "5003"
    FILE_ERR = '6000'


def response_collect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_result = func(*args, **kwargs)
        resp = make_response(func_result)
        resp.headers['Authorization'] = g.token
        return resp

    return wrapper
