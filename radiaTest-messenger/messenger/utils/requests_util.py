import requests
import json
from flask import current_app

from . import DateEncoder
from .response_util import RET


def do_request(method, url, params=None, body=None, headers=None, timeout=30, obj=None):
    """

    :param headers: dict
    :param method: http method
    :param url: http
    :param params: dict url querystring
    :param body: dict
    :param timeout: second
    :param obj: callback object, support list/dict/object/func
    :return:
    """

    try:
        if method.lower() not in ['get', 'post', 'put', 'delete']:
            return -1
        
        resp = requests.request(
            method.lower(), 
            url, 
            params=params, 
            data=json.dumps(body, cls=DateEncoder), 
            timeout=timeout, 
            headers=headers
        )

        if resp.status_code not in [
            requests.codes.ok, 
            requests.codes.created, 
            requests.codes.no_content
        ]:
            current_app.logger.info(
                'response code error! status_code {}: {}'.format(
                    resp.status_code,
                    resp.text,
                )
            )
            return 1
        
        if obj is not None:
            if isinstance(obj, list):
                obj.extend(resp.json())
            elif isinstance(obj, dict):
                obj.update(resp.json())
            elif callable(obj):
                obj(resp)
        return 0

    except requests.exceptions.ReadTimeout as e:
        current_app.logger.error(
            f"request read time out: {e}"
        )
        return 4
    
    except requests.exceptions.Timeout as e:
        current_app.logger.error(
            f"request time out: {e}"
        )
        return 2
    
    except requests.exceptions.SSLError as e:
        current_app.logger.error(
            f"request ssl error: {e}"
        )
        return -2
    
    except requests.exceptions.RequestException as e:
        current_app.logger.error(
            f"request exception: {e}"
        )
        return 3

def query_request(api, params, auth):
    _resp = dict()
    _r = do_request(
        method="get",
        url="https://{}{}".format(
            current_app.config.get("SERVER_ADDR"),
            api,
        ),
        params=params,
        headers={
            "content-type": "application/json;charset=utf-8",
            "authorization": auth
        },
        obj=_resp,
    )

    item = None
    if _r == 0 and _resp.get("error_code") == RET.OK:
        item = _resp.get("data")

    return item

def update_request(api, body, auth):
    _resp = dict()
    _r = do_request(
        method="put",
        url="https://{}{}".format(
            current_app.config.get("SERVER_ADDR"),
            api,
        ),
        body=body,
        headers={
            "content-type": "application/json;charset=utf-8",
            "authorization": auth
        },
        obj=_resp,
    )
    if _r != 0 or _resp.get("error_code") != RET.OK:
        raise RuntimeError("fail to update this item")
    
    return _resp

def create_request(api, body, auth):
    _resp = dict()
    _r = do_request(
        method="post",
        url="https://{}{}".format(
            current_app.config.get("SERVER_ADDR"),
            api,
        ),
        body=body,
        headers={
            "content-type": "application/json;charset=utf-8",
            "authorization": auth
        },
        obj=_resp,
    )

    item = None
    if _r == 0 and _resp.get("error_code")==RET.OK:
        item = _resp.get("data")

    return item
