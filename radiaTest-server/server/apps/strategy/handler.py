# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2023/3/20 14:00:00
# License : Mulan PSL v2
#####################################
# 测试设计(Strategy)相关接口的handler层

import abc
import json
from math import floor
import os
import subprocess

from flask import current_app, request, Response, current_app, g, jsonify
import sqlalchemy
import requests
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from celeryservice import celeryconfig
from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.db import pdbc
from server.utils.response_util import RET
from server.model.qualityboard import Feature
from server.model.organization import Organization
from server.model.product import Product
from server.model.user import User
from server.model.strategy import ReProductFeature, Strategy, StrategyTemplate, StrategyCommit
from server.utils.db import Insert, Edit, Delete, Precise, collect_sql_error
from server.utils.permission_utils import GetAllByPermission
from server.model.testcase import CaseNode, Baseline
from server.model.baselinetemplate import BaselineTemplate, BaseNode
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server.utils.response_util import value_error_collect
from server.apps.qualityboard.handlers import FeatureHandler, OpenEulerReleasePlanHandler
from server.utils.requests_util import do_request
from server.utils.md_util import MdUtil



class StrategyHandler:
    def __init__(self, table, re_table=None, **kwargs) -> None:
        self.table = table
        self.re_table = re_table
        self.filter_params = list()
        if kwargs.get("filter_params"):
            self.filter_params = kwargs.get("filter_params")


    def get_query(self, _has_re_table=None):
        _query = db.session.query(self.table)
        if _has_re_table:
            _query = db.session.query(self.re_table, self.table)

        return _query


    def get_re_query(self, _has_table=None):
        re_query = db.session.query(self.re_table)
        if _has_table:
            re_query = db.session.query(self.table, self.re_table)
        return re_query



    @abc.abstractmethod
    def get_filter_params(self):
        pass



class ProductFeatureHandler(StrategyHandler):
    def get_filter_params(self, product_id, query = None):
        filter_params = [
            self.re_table.product_id == product_id,
            self.table.id == self.re_table.feature_id,
            self.re_table.is_new == query.is_new,
        ]

        return filter_params



class InheritFeatureHandler:
    def __init__(self, product_id = None) -> None:
        self.fs = list() 
        self.product_id = product_id
        self._data = list()
    

    def create_relate_data(self, body, products):
        for _p in products:
            _body = {
                "product_id": _p.id,
                **body.__dict__
            }
            _id = NodeHandler(
                ReProductFeature, 
                _body, 
            ).create_batch_node()
            self._data.append(_id)

        return self._data


    def get_all_feature(self, product):
        _fs = ReProductFeature.query.filter(
            ReProductFeature.product_id == product.id,
        ).all() 
        self.fs.extend(_fs)
        return self.fs


    def create_inherit_data(self, fs):
        for _f in fs:
            _body = _f.to_json()
            _body.update({
                "product_id": self.product_id,
                "is_new": False
            })
            del _body["product_feature_id"]
            _id = NodeHandler(
                ReProductFeature, 
                _body, 
            ).create_batch_node()
            self._data.append(_id)
        self._data = list(set(self._data))

        return self._data


    def get_product_features(self, product_id, query=None):
        return_data = list()
        _handler = ProductFeatureHandler(
            table=Feature, 
            re_table=ReProductFeature, 
            product_id=product_id
        )
        
        _query = _handler._get_query(_has_re_table=True)
        filter_params = _handler.get_filter_params(
            _is_inherit_all = False,
            query = query
        )

        product_features = _query.filter(*filter_params).all() 
        for feature in  product_features:
            _feature_data = {
                **feature[0].to_json(),
                **feature[1].to_json()
            }
            return_data.append(_feature_data)
        
        return jsonify(
            data = return_data,
            error_code = RET.OK,
            error_msg = "OK"
        )



class PdbcHandler:
    def __init__(self, table, body: dict, **kwargs) -> None:
        self.table = table
        self.body = body


    @abc.abstractmethod
    def _get_query(self):
        self.query = db.session.query(self.table)
        self.table_data = self.query.filter(*self.body).first()
        

    @pdbc
    def create(self):
        table_row = self.table(**self.body)
        db.session.add(table_row)
        db.session.flush()
        
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e
        return table_row

    @pdbc
    def get(self):
        return self.table_data


    @pdbc
    def get_query_params(self):
        table_datas = self.query.filter(*self.body).all()
        return table_datas


    @pdbc
    def put(self):
        for key, value in self.body.items():
            if value is not None:
                setattr(self.table_data, key, value)
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e


    @pdbc
    def delete(self):
        db.session.delete(self.table_data)
        try:
            db.session.commit()
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise e



class NodeHandler(PdbcHandler):
    def __init__(self, table, body: dict, t_return: str = "json_id", **kwargs) -> None:
        super().__init__(table, body, **kwargs)
        self.t_return = t_return
        if kwargs.get("product_id"):
            self.product_id = kwargs.get("product_id")
        self.filter_params = list()
        if kwargs.get("filter_params"):
            self.filter_params = kwargs.get("filter_params")

    
    @property
    def org_id(self):
        return redis_client.hget(
            RedisKey.user(g.gitee_id), 
            "current_org_id"
        )

    @property
    def addition_body(self):
        return {
            "creator_id": g.gitee_id,
            "org_id": self.org_id
        }


    def _get_all(self, is_all: bool = False):
        if is_all:
            self.table_data = self.query.filter(
                *self.filter_params
            ).all()
        else:
            self.table_data = self.query.filter(
                *self.filter_params
            ).first()


    def _set_key_mode(self, key , value):
        if key == "title" or key == "feature":
            self.filter_params.append(
                getattr(self.table, key).like(f'%{value}%')
            )
        else:
            self.filter_params.append(getattr(self.table, key) == value)


    def _get_query(self, is_modify: bool = False, is_all: bool = False):
        
        self.query = StrategyHandler(self.table).get_query()
        
        if not self.filter_params:            
            if self.body:
                
                for key, value in self.body.items():
                    if value is None: 
                        continue
                    if is_modify and key == "id":
                        self.filter_params.clear()
                        self.filter_params.append(getattr(self.table, key) == value)
                        break
                    self._set_key_mode(key, value)
        self._get_all(is_all)


    def _check_exist(self, is_exist_error: bool = False, 
                is_modify: bool = False, is_all: bool = False):
        
        self._get_query(is_modify, is_all)
        
        if self.table_data and is_exist_error:
            raise ValueError("Related data is already exist.") 
        elif (not self.table_data) and (not is_exist_error):
            raise ValueError("Related data is not exist.") 


    def _return_resp(self, _data):
        return jsonify(
            data = _data,
            error_code = RET.OK,
            error_msg = "OK"
        )


    def _generate_return(self, _data):
        if isinstance(_data, Response):
            raise ValueError("Data Error: _data")
        params = {
            "obj": _data,
            "int": _data.id,
            "json_id": self._return_resp({
                "id": _data.id
            }),
            "json_all": self._return_resp(
                _data.to_json()
            )
        }
        
        if self.t_return not in params.keys():
            return jsonify(
                error_code = RET.VERIFY_ERR,
                error_msg = f'The type of return is should be in \
                    ["obj", "int", "json_id", "json_all"].' 
            )
        
        for key, value in params.items():
            if self.t_return == key:
                return value


    def get_all_children(self, node):
        if not node.children:
            return node.to_json()
        
        result = {
            "children": [],
            **node.to_json(),
        }
        for child in node.children:
            result["children"].append(
                self.get_all_children(child)
            )
        return result


    @pdbc
    def create_node(self, is_addition_body: bool = False):
        if is_addition_body:
            self.body.update(**self.addition_body)

        self._check_exist(is_exist_error = True)
        table_row = self.create()
        
        return self._generate_return(table_row)


    @pdbc
    def create_batch_node(self, is_addition_body: bool = False):
        if is_addition_body:
            self.body.update(**self.addition_body)
        self._get_query()
        if self.table_data:
            return self.table_data.id
        table_row = self.create()
        return table_row.id


    @pdbc
    def get_node(self):
        self._check_exist(is_exist_error = False)
        self.t_return = "json_all"
        return self._generate_return(self.table_data)


    @pdbc
    def get_query_nodes(self):
        self._check_exist(is_exist_error = False, is_all = True) 
        return jsonify(
            data = [t_d.to_json() for t_d in self.table_data],
            error_code = RET.OK,
            error_msg = "OK"
        )


    @pdbc
    def put_node(self):
        self._check_exist(is_exist_error = False, is_modify = True) 
        self.put()


    @pdbc
    def delete_node(self):
        self._check_exist(is_exist_error = False) 
        self.delete()



class StrategyEventHandler(StrategyHandler):

    def __init__(self, table, re_table=None, **kwargs) -> None:
        super().__init__(table, re_table, **kwargs)
        if kwargs.get("strategy_id"):
            self.strategy_id = kwargs.get("strategy_id")
            self._filter = [
                self.table.strategy_id == self.strategy_id,
                self.table.strategy_id == self.re_table.id
            ]
        
        if kwargs.get("strategy_commit_id"):
            self.strategy_commit_id = kwargs.get("strategy_commit_id")
            self._filter = [
                self.table.id == self.strategy_commit_id,
                self.table.strategy_id == self.re_table.id
            ]
        
        self.strategy_filter = list()
        if kwargs.get("product_feature_id"):
            self.product_feature_id = kwargs.get("product_feature_id")
            self._filter = [
                self.re_table.product_feature_id == self.product_feature_id,
                self.table.strategy_id == self.re_table.id
            ]
            self.strategy_filter = [
                self.re_table.product_feature_id == self.product_feature_id
            ]


    def check_strategy(self):
        if self.strategy_filter:
            _strategy = self.get_re_query().filter(*self.strategy_filter).first()
        else:
            _strategy = self.get_re_query().filter_by(
                id = self.strategy_id
            ).first()
        if _strategy:
            return True, _strategy
        else:
            return False, None


    def check_strategy_exist(self, should_exist = True):
        is_exist, _strategy = self.check_strategy()
        
        if (not is_exist) and should_exist:
            raise ValueError("The strategy is not exist.") 
        elif is_exist and (not should_exist):
            raise ValueError("The strategy is already exist.") 
        return _strategy


    def check_commit(self):
        _strategy_commit = self.get_query().filter(*self._filter).first()
        if _strategy_commit:
            return True
        else:
            return False
        

    def check_commit_not_exist(self):
        is_exist = self.check_commit()
        
        if is_exist:
            raise ValueError(
                "Cannot be deleted because there is strategy-commit data."
            ) 

    
    def check_commit_creator(self):
        _strategy_commit = self.get_query().filter(
            *self._filter,
            self.re_table.creator_id != g.gitee_id
        ).first()
        
        if _strategy_commit:
            raise ValueError("The strategy-commit has been locked by other user.") 


    def check_commit_status(self):
        _strategy_commit = self.get_query().filter(
            *self._filter,
            self.table.commit_status != "staged"
        ).first()
        
        if _strategy_commit:
            raise ValueError(
                "The commit_status of strategy is invalid, should be staged."
            ) 


    def check_product_feature_exist(self):
        r_p_f = ReProductFeature.query.filter_by(
            id = self.product_feature_id
        ).first()
        
        if not r_p_f:
            raise ValueError(
                "The ReProductFeature is not exist."
            ) 

    def check_feature_exist(self):
        feature = ReProductFeature.query.filter(
            ReProductFeature.id == self.product_feature_id,
            Feature.id == ReProductFeature.feature_id
        ).first()
        
        if not feature:
            raise ValueError(
                "The feature is not exist."
            ) 

    def create_strategy(self, product_feature_id, body):
        feature = Feature.query.join(ReProductFeature).filter(
            ReProductFeature.id == product_feature_id,
            ReProductFeature.feature_id == Feature.id
        ).first()

        handler = StrategyEventHandler(
            StrategyCommit,
            Strategy,
            product_feature_id = product_feature_id
        )
        handler.check_product_feature_exist() 
        handler.check_commit_not_exist()

        try:
            strategy_id = NodeHandler(
                Strategy,
                {
                    "product_feature_id": product_feature_id,
                    "file_type": "New",
                    "tree": json.dumps(
                        {"data": {
                            "text": feature.feature, 
                            "id": 0
                        }}
                    )
                },
                t_return = "int"
            ).create_node(
                is_addition_body = True
            )

            return NodeHandler(
                StrategyCommit,
                {
                    "strategy_id": strategy_id,
                    "commit_status": "staged",
                    "commit_tree": json.dumps(body.tree)
                },
            ).create_node()
        except (RuntimeError, ValueError) as e:
            current_app.logger.error(str(e))
            if isinstance(strategy_id, int):
                NodeHandler(
                    Strategy,
                    {"id": strategy_id}
                ).delete_node()
            return jsonify(
                error_code = RET.BAD_REQ_ERR,
                error_msg = str(e)
            )



class GiteePrHandler():
    @property
    def current_org(self):
        org_id = redis_client.hget(
            RedisKey.user(g.gitee_id), "current_org_id")
        org = Organization.query.filter_by(id=org_id).first()
        return org


    @property
    def access_token(self):
        # 永久token
        return celeryconfig.v5_access_token


    def add_update(self, act, url, data, filter = None):
        
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



class CommitHandler():
    
    def __init__(self, strategy_id) -> None:

        user = User.query.filter_by(gitee_id=g.gitee_id).first()
        self.user_params={
                "owner": "radiaTest_bot",
                "repo": "QA", 
                "head": f'radiaTest_bot:radiaTest-{user.gitee_name}',
                "base": "master", 
                "refs": "master",
                "branch_name": f'radiaTest-{user.gitee_name}',  
                "gitee_password": "Mugen12#$",
                "email": "radiatest@163.com", 
            }
        self.enterprise_params={
            "owner": "openEuler", 
            "repo": "QA", 
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
            id = strategy.product_feature_id
        ).first()

        if not re_row:
            return jsonify(
                error_code = RET.NO_DATA_ERR,
                error_msg = "The data is not exist."
            )
        
        return re_row


    @property
    def title(self):
        feature = Feature.query.filter_by(
            id = self.re_row.feature_id
        ).first()
        
        return feature.feature
    
    
    def get_path(self):
        product = Product.query.filter_by(
            id = self.re_row.product_id
        ).first()

        if not product:
            return jsonify(
                error_code = RET.NO_DATA_ERR,
                error_msg = "The product is not exist."
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
                exitcode, _ = subprocess.getstatusoutput(
                    "pushd {}/QA && git pull && popd".format(
                        file_path
                    )
                )
            else:
                exitcode, _ = subprocess.getstatusoutput(
                    "pushd {} && git clone https://gitee.com/radiaTest_bot/QA -b {} && popd".format(
                        file_path,
                        self.user_params.get("branch_name")
                    )
                )
            if exitcode != 0:
                return None

            self.put_feature_strategy(file_path, md_content)

            # git commit
            exitcode, msg = subprocess.getstatusoutput(
                "cd {}/QA && git config user.name {} && git config user.email {}".format(
                    file_path,
                    self.user_params.get("branch_name"),
                    self.user_params.get("email"),
                )
            )
            if exitcode != 0:
                raise RuntimeError(f'Git-config Error: {msg}')
  
            exitcode, msg = subprocess.getstatusoutput(
                "cd {}/QA && git add . && git commit -m {} ".format(
                    file_path,
                    self.title,
                )
            )
            if exitcode != 0:
                raise RuntimeError(f'Git-command Error: {msg}')

            exitcode, msg = subprocess.getstatusoutput(
                "cd {}/QA ".format(
                    file_path,
                )
            )

            exitcode1, msg = subprocess.getstatusoutput(
                "sh /opt/radiaTest/radiaTest-server/server/apps/strategy/push.sh {}/QA".format(
                file_path
            ))
        except (RuntimeError, ValueError) as e:
            if os.path.exists(file_path):
                current_app.logger.error(file_path)
                exitcode, _ = subprocess.getstatusoutput(
                        "rm -rf {}".format(file_path)
                    )
            raise ValueError(str(e))
    
