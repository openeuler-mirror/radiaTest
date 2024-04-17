# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author :
# email :
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################

# 基线模板(Baseline_template)的model
from server import db
from server.model.base import BaseModel, PermissionBaseModel


base_node_family = db.Table(
    'base_node_family',
    db.Column('parent_id', db.Integer, db.ForeignKey(
        'base_node.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey(
        'base_node.id'), primary_key=True)
)


class BaselineTemplate(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "baseline_template"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(64), nullable=False, default="group")
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    openable = db.Column(db.Boolean(), default=True)
    base_node = db.relationship(
        "BaseNode", backref="baseline_template", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        return_data = {
            "id": self.id,
            "title": self.title,
            'openable': self.openable,
            "type": self.type,
            "group_id": self.group_id,
            "org_id": self.org_id,
        }
        return return_data

    def to_dict(self):
        _dict = self.__dict__
        _dict.update({
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        return _dict


class BaseNode(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "base_node"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(64), nullable=False, default="directory")
    is_root = db.Column(db.Boolean(), default=True)
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    baseline_template_id = db.Column(db.Integer(), db.ForeignKey("baseline_template.id"))
    case_node_id = db.Column(db.Integer(), db.ForeignKey("case_node.id"))

    children = db.relationship(
        "BaseNode",
        secondary=base_node_family,
        primaryjoin=(base_node_family.c.parent_id == id),
        secondaryjoin=(base_node_family.c.child_id == id),
        backref=db.backref('parent', lazy='dynamic'),
        lazy='dynamic',
        cascade="all, delete"
    )

    def to_json(self):
        return_data = {
            "data": {
                "id": self.id,
                "text": self.title,
            },
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "baseline_template_id": self.baseline_template_id,
            "case_node_id": self.case_node_id,
            "is_root": self.is_root,
        }
        return return_data

    def to_dict(self):
        _dict = self.__dict__
        _dict.update({
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        return _dict
