import requests
from flask import current_app


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
        resp = requests.request(method.lower(), url, params=params, data=body, timeout=timeout, headers=headers)
        if resp.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.no_content]:
            current_app.logger.info(f'response code error! status_code {resp.status_code}')
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
        current_app.logger.error(f"request read time out: {e}")
        return 4
    except requests.exceptions.Timeout as e:
        current_app.logger.error(f"request time out: {e}")
        return 2
    except requests.exceptions.SSLError as e:
        current_app.logger.error(f"request ssl error: {e}")
        return -2
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"request exception: {e}")
        return 3


if __name__ == "__main__":
    do_request("get", "https://www.baidu.com")
