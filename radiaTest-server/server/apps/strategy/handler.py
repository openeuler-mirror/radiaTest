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
from server.utils.shell import run_cmd


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
        return celeryconfig.v5_access_token

    def add_update(self, act, url, data, filter=None):

        data.update({"access_token": self.access_token})

        _resp = requests.request(
            method=act,
            url=url,
            data=json.dumps(data),
            headers=current_app.config.get("HEADERS"),
        )
        _resp.encoding = _resp.apparent_encoding

        if (_resp.status_code != 200 and act == "PUT") or (
                _resp.status_code != 201 and act == "POST" and (
                filter not in _resp.text)
        ):
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
            url=url, params=_params, headers=current_app.config.get("HEADERS")
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
            "gitee_password": "Mugen12#$",  # radiaTest机器人git密码
            "email": "radiatest@163.com",  # radiaTest机器人公共账户gitee邮箱
        }
        self.enterprise_params = {
            "owner": "openEuler",  # 企业组织
            "repo": "QA",  # 企业仓库
        }
        self.strategy_id = strategy_id

    def create_pull_request(self, body):
        _url = "https://gitee.com/api/v5/repos/{}/{}/pulls".format(
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
        _url = "https://gitee.com/api/v5/repos/{}/{}/pulls".format(
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

    def create_fork(self, body=dict()):
        _url = "https://gitee.com/api/v5/repos/{}/{}/forks".format(
            self.enterprise_params.get("owner"),
            self.enterprise_params.get("repo")
        )

        GiteePrHandler().add_update(
            act="POST",
            url=_url,
            data=body,
            filter="存在同名的仓库"
        )

    def create_branch(self, body=dict()):
        _url = "https://gitee.com/api/v5/repos/{}/{}/branches".format(
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
        _url = "https://gitee.com/api/v5/repos/{}/{}".format(
            self.user_params.get("owner"),
            self.user_params.get("repo")
        )

        GiteePrHandler().query(
            url=_url,
            params=body,
        )

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

        with open(export_file, 'w') as f:
            f.writelines(md_content)
        return export_file

    def git_operate(self, md_content):
        file_path = f'/tmp/{self.user_params.get("branch_name")}'
        if not os.path.exists(file_path):
            os.mkdir(file_path)
        try:
            if os.path.isdir(f'{file_path}/QA'):
                exitcode, _, _ = run_cmd("pushd {}/QA && git pull && popd".format(file_path))
            else:
                exitcode, _, _ = run_cmd("pushd {} " \
                                         "&& git clone https://gitee.com/radiaTest_bot/QA -b {} && popd".format(
                    file_path,
                    self.user_params.get("branch_name")
                )
                )

            if exitcode != 0:
                return None

            # modify content写入文件

            export_file = self.put_feature_strategy(file_path, md_content)

            # git commit
            exitcode, out, msg = run_cmd("cd {}/QA && git config user.name {} && git config user.email {} " \
                                         "&& git add . && git commit -m {}".format(
                file_path,
                self.user_params.get("branch_name"),
                self.user_params.get("email"),
                self.title,
                )
            )

            if exitcode != 0:
                raise RuntimeError(f'Git operate Error: {msg}')
            _, _, _ = run_cmd("sh /opt/radiaTest/radiaTest-server/server/apps/strategy/push.sh {}/QA".format(
                    file_path
                )
            )
        except (RuntimeError, ValueError) as e:
            if os.path.exists(file_path):
                _, _, _ = run_cmd("rm -rf {}".format(file_path))
