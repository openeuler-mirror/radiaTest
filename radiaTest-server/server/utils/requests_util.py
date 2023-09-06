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

import json
import requests
from flask import current_app

from server.utils import DateEncoder


def do_request(method, url, params=None, body=None, headers=None, timeout=30, obj=None, encoder=DateEncoder, verify=True):
    """
    :param headers: dict
    :param method: http method
    :param url: http
    :param params: dict url querystring
    :param body: dict
    :param timeout: second
    :param obj: callback object, support list/dict/object/func
    :param encoder: JSON encoder
    :param verify: ssl pem / not verify
    :return:
    """

    try:
        if method.lower() not in ['get', 'post', 'put', 'delete']:
            return -1
        
        if encoder is not None:
            body = json.dumps(body, cls=encoder)

        resp = requests.request(
            method.lower(), 
            url, 
            params=params, 
            data=body,
            timeout=timeout, 
            headers=headers,
            verify=verify,
        )
        
        if resp.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.no_content]:
            current_app.logger.warn(
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
        current_app.logger.error(f"request read time out: {e}")
        return 4
    except requests.exceptions.Timeout as e:
        current_app.logger.error(f"request time out: {e}")
        return 2
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"request exception: {e}")
        if isinstance(e, requests.exceptions.SSLError):
            raise e
        return 3
