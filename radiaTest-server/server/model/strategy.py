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
# Date : 2023/2/8 14:00:00
# License : Mulan PSL v2
#####################################
# 测试设计(Strategy)的model层

from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import backref

from server import db
from server.model.base import BaseModel, PermissionBaseModel


class ReProductFeature(BaseModel, db.Model):
    __tablename__ = "re_product_feature"

    id = db.Column(db.Integer(), primary_key=True)
    is_new = db.Column(db.Boolean(), default=False)
    product_id = db.Column(db.Integer(), db.ForeignKey("product.id"))
    feature_id = db.Column(db.Integer(), db.ForeignKey("feature.id"))
    strategy = db.relationship(
        "Strategy", backref="re_product_feature"
    )

    def to_json(self):
        return_data = {
            "product_feature_id": self.id,
            "product_id": self.product_id,
            "is_new": self.is_new,
            "feature_id": self.feature_id
        }
        return return_data


class Strategy(BaseModel, db.Model):
    __tablename__ = "strategy"

    id = db.Column(db.Integer(), primary_key=True)
    tree = db.Column(LONGTEXT())
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    file_type = db.Column(db.String(255), nullable=False)
    product_feature_id = db.Column(db.Integer(), 
        db.ForeignKey("re_product_feature.id"), 
        unique=True
    )
    strategy_commit = db.relationship(
        "StrategyCommit", backref="strategy"
    )    
    

    def to_json(self):
        return_data = {
            "id": self.id,
            "tree": self.tree,
            "org_id": self.org_id,
            "product_feature_id": self.product_feature_id,
        }
        return return_data


class StrategyCommit(BaseModel, db.Model):
    __tablename__ = "strategy_commit"

    id = db.Column(db.Integer(), primary_key=True)
    commit_tree = db.Column(LONGTEXT())
    commit_status = db.Column(db.String(255), nullable=False)
    strategy_id = db.Column(db.Integer(), db.ForeignKey("strategy.id"), unique=True)


    def to_json(self):
        return_data = {
            "id": self.id,
            "commit_tree": self.commit_tree,
            "commit_status": self.commit_status,
            "strategy_id": self.strategy_id,
        }
        return return_data

    def to_combine_json(self):
        return_data = {
            "strategy_commit_id": self.id,
            "strategy_commit_status": self.commit_status,
            "strategy_id": self.strategy_id,
        }
        return return_data


class StrategyTemplate(BaseModel, db.Model):
    __tablename__ = "strategy_template"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False, unique=True)
    tree = db.Column(LONGTEXT())
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))


    def to_json(self):
        return_data = {
            "id": self.id,
            "title": self.title,
            "tree": self.tree,
            "org_id": self.org_id,
        }
        return return_data
