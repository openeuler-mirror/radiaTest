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

import abc
import json

from flask.globals import current_app
import requests
from flask import g, jsonify

from server import redis_client
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error
from server.utils.response_util import RET
from server.model.organization import Organization


class BaseOpenApiHandler:
    def __init__(self, table=None, namespace=None, org_id=None):
        self.table = table
        self.namespace = namespace
        self.org_id = org_id

    @abc.abstractmethod
    def gitee_2_radia(self):
        pass

    @abc.abstractmethod
    def radia_2_gitee(self):
        pass

    @property
    def headers(self):
        return current_app.config.get("HEADERS")

    @property
    def access_token(self):
        return self.current_org.enterprise_token

    @property
    def current_org(self):
        org = Organization.query.filter_by(id=self.org_id).first()
        return org

    @collect_sql_error
    def add_update(self, act, url, data, schema, handler):
        data.update({"access_token": self.access_token})

        _resp = requests.request(
            method=act,
            url=url,
            data=json.dumps(schema(**data).__dict__),
            headers=self.headers,
        )

        _resp.encoding = _resp.apparent_encoding

        if (_resp.status_code != 200 and act == "PUT") or (
            _resp.status_code != 201 and act == "POST"
        ):
            current_app.logger.error(_resp.text)
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to add_update through gitee v8 openAPI",
            )

        gitee_resp = json.loads(_resp.text)

        radia_resp = self.gitee_2_radia(gitee_resp)

        _ = handler(self.table, radia_resp).single(self.table, self.namespace)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @collect_sql_error
    def query(self, url, params=None):
        _params = {
            "access_token": self.access_token,
        }
        if params is not None and isinstance(params, dict):
            _params.update(params)

        _resp = requests.get(
            url=url, params=_params, headers=self.headers
        )

        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="fail to get data through gitee openAPI",
            )

        return jsonify(error_code=RET.OK, error_msg="OK", data=_resp.text)