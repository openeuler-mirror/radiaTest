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
import os
import stat

from flask import current_app, g, jsonify
import requests

from celeryservice import celeryconfig
from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.model.qualityboard import Feature
from server.model.organization import Organization
from server.model.product import Product
from server.model.user import User
from server.model.strategy import ReProductFeature, Strategy
from server.utils.db import Insert, collect_sql_error


class FeatureHandler:
    def __init__(self, filter_params=None, exists=None, body=None):
        self._body = body
        if filter_params:
            feature = Feature.query.filter(*filter_params).all()
            if not feature and not exists:
                raise RuntimeError("feature is not exists")
            elif feature and exists:
                raise RuntimeError("feature is already exists")
            else:
                pass

    def create_node(self):
        feature_id = Insert(Feature, self._body).insert_id()
        return feature_id

    def get_node(self):
        feature = Feature.query.filter_by(id=self._body.get("id")).first()
        return feature

    def put_node(self, feature):
        for key, value in self._body.item():
            if value is not None:
                setattr(feature, key, value)
        feature.add_update()

    def delete_node(self):
        feature = Feature.query.filter_by(id=self._body.get("id")).first()
        if feature:
            db.session.delete(feature)
            db.session.commit()


class InheritFeatureHandler:
    def __init__(self, product_id=None) -> None:
        self.fs = list()
        self.product_id = product_id
        self._data = list()

    @staticmethod
    def create_relate_data(body, product_id):
        _body = {
            "product_id": product_id,
            **body.__dict__
        }
        re_product_feature_id = Insert(
            ReProductFeature,
            _body,
        ).insert_id()

        return re_product_feature_id

    def get_inherit_feature(self, product):
        _fs = ReProductFeature.query.filter(
            ReProductFeature.product_id == product.id,
            ReProductFeature.is_new == 0
        ).all()
        self.fs.extend(_fs)
        return self.fs


class GiteePrHandler():
    @property
    def current_org(self):
        org_id = redis_client.hget(
            RedisKey.user(g.user_id), "current_org_id")
        org = Organization.query.filter_by(id=org_id).first()
        return org

    @property
    def access_token(self):
        return celeryconfig.V5_ACCESS_TOKEN

    def add_update(self, act, url, data, filters=None):

        data.update({"access_token": self.access_token})

        _resp = requests.request(
            method=act,
            url=url,
            data=json.dumps(data),
            headers=current_app.config.get("HEADERS"),
        )
        _resp.encoding = _resp.apparent_encoding
        put_res = (_resp.status_code != 200 and act == "PUT")
        post_res = (_resp.status_code != 201 and act == "POST" and (filters not in _resp.text))
        if put_res or post_res:
            current_app.logger.error(_resp.text)
            raise ValueError(
                "fail to add_update through gitee v5 openAPI or has exist."
            )

        return _resp

    @collect_sql_error
    def query(self, url, params=None):
        _params = {
            "access_token": self.access_token,
        }
        if params is not None and isinstance(params, dict):
            _params.update(params)

        _resp = requests.get(
            url=url,
            params=_params,
            headers=current_app.config.get("HEADERS"),
            timeout=30
        )

        _resp.encoding = _resp.apparent_encoding

        if _resp.status_code != 200:
            current_app.logger.error(_resp.text)
            return ValueError(
                "fail to get data through gitee openAPI"
            )

        return _resp.text


class CommitHandler:
    def __init__(self, strategy_id) -> None:
        user = User.query.filter_by(user_id=g.user_id).first()
        self.user_params = {
            "owner": "radiaTest_bot",  # radiaTest机器人公共账户
            "repo": "QA",  # 公共账户仓库
            "head": f'radiaTest_bot:radiaTest-{user.gitee_name}',  # pr源分支
            "base": "master",  # pr目的分支
            "refs": "master",  # 索引分支
            "branch_name": f'radiaTest-{user.gitee_name}',  # 新分支名称
            "gitee_password": current_app.config.get("GITEE_PASSWORD"),  # radiaTest机器人git密码
            "email": current_app.config.get("GITEE_EMAIL"),  # radiaTest机器人公共账户gitee邮箱
        }
        self.enterprise_params = {
            "owner": "openEuler",  # 企业组织
            "repo": "QA",  # 企业仓库
        }
        self.strategy_id = strategy_id

    @property
    def re_row(self):
        strategy = Strategy.query.filter_by(id=self.strategy_id).first()
        re_row = ReProductFeature.query.filter_by(
            id=strategy.product_feature_id
        ).first()

        if not re_row:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The data is not exist."
            )

        return re_row

    @property
    def title(self):
        feature = Feature.query.filter_by(
            id=self.re_row.feature_id
        ).first()

        return feature.feature

    def create_pull_request(self, body):
        _url = "{}/repos/{}/{}/pulls".format(
            current_app.config.get("GITEE_V5"),
            self.enterprise_params.get("owner"),
            self.enterprise_params.get("repo")
        )

        body.update({
            "head": self.user_params.get("head"),
            "base": self.user_params.get("base"),
        })

        GiteePrHandler().add_update(
            act="POST",
            url=_url,
            data=body,
            filter="已存在相同源分支"
        )

    def get_pull_request(self, body):
        _url = "{}/repos/{}/{}/pulls".format(
            current_app.config.get("GITEE_V5"),
            self.enterprise_params.get("owner"),
            self.enterprise_params.get("repo")
        )

        body.update({
            "head": self.user_params.get("head"),
            "base": self.user_params.get("base"),
        })

        GiteePrHandler().query(
            url=_url,
            params=body,
        )

    def create_fork(self, body: dict = None):
        _url = "{}/repos/{}/{}/forks".format(
            current_app.config.get("GITEE_V5"),
            self.enterprise_params.get("owner"),
            self.enterprise_params.get("repo")
        )

        GiteePrHandler().add_update(
            act="POST",
            url=_url,
            data=body,
            filter="存在同名的仓库"
        )

    def create_branch(self, body: dict = None):
        _url = "{}/repos/{}/{}/branches".format(
            current_app.config.get("GITEE_V5"),
            self.user_params.get("owner"),
            self.user_params.get("repo")
        )
        body.update({
            "refs": self.user_params.get("refs"),
            "branch_name": self.user_params.get("branch_name"),
        })

        GiteePrHandler().add_update(
            act="POST",
            url=_url,
            data=body,
            filter="分支名已存在"
        )

    def get_branch(self, body=None):
        _url = "{}/repos/{}/{}".format(
            current_app.config.get("GITEE_V5"),
            self.user_params.get("owner"),
            self.user_params.get("repo")
        )

        GiteePrHandler().query(
            url=_url,
            params=body,
        )

    def get_path(self):
        product = Product.query.filter_by(
            id=self.re_row.product_id
        ).first()

        if not product:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The product is not exist."
            )

        _vs = product.version.split("-")

        _version1 = f'{_vs[0]}_{_vs[1]}'
        _version2 = f'{_vs[0]} {_vs[1]}'

        feature_strategy_name = f'{product.name} {_version2} {self.title} 特性测试策略.md'
        product_strategy = f'{product.name}_{_version1}'
        product_path = f'/QA/Test_Strategy/{product_strategy}'

        return product_path, feature_strategy_name

    def put_feature_strategy(self, file_path, md_content) -> str:
        product_path, feature_strategy_name = self.get_path()
        product_path = f'{file_path}{product_path}'

        export_file = f'{product_path}/{feature_strategy_name}'

        if not os.path.exists(product_path):
            os.mkdir(product_path)

        flags = os.O_RDWR | os.O_CREAT
        mode = stat.S_IRUSR | stat.S_IWUSR
        with os.fdopen(os.open(export_file, flags, mode), 'w') as fout:
            fout.writelines(md_content)
            fout.close()

        return export_file


