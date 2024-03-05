# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2023/01/11
# @License : Mulan PSL v2
#####################################

from enum import Enum

from sqlalchemy import func
from sqlalchemy.orm import aliased

from server.model import BaseModel, PermissionBaseModel
from server.model.permission import Role, ReUserRole
from server import db


class GroupRole(Enum):
    create_user = 1
    admin = 2
    user = 3
    no_reviewer = 0


class Group(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "group"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    is_delete = db.Column(db.Boolean(), default=False, nullable=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    influence = db.Column(db.Integer(), nullable=False, default=0)
    behavior = db.Column(db.Float(), nullable=False, default=100.0)

    rank = db.Column(db.Integer())

    re_user_group = db.relationship("ReUserGroup", cascade="all, delete", backref="group")

    case_nodes = db.relationship("CaseNode", cascade="all, delete", backref="group")

    roles = db.relationship("Role", cascade="all, delete", backref="group")

    re_group_requirment_publisher = db.relationship("RequirementPublisher", backref="group")
    re_group_requirment_acceptor = db.relationship("RequirementAcceptor", backref="group")

    def add_update(self, table=None, namespace=None, broadcast=False):
        from sqlalchemy.exc import IntegrityError
        from flask import current_app
        if self.is_delete:
            try:
                super().delete(table, namespace, broadcast)
                return True
            except IntegrityError as e:
                current_app.logger.error(f'database operate error -> {e}')
                return False
        else:
            super().add_update(table, namespace, broadcast)
            return True

    def to_summary(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'influence': self.influence,
            'behavior': self.behavior,
            'rank': self.rank,
        }

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'is_delete': self.is_delete,
            'influence': self.influence,
            'behavior': self.behavior,
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            'update_time': self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def create(name, description=None, avatar_url=None, creator_id=None, org_id=None, permission_type=None):
        new_recode = Group()
        new_recode.name = name
        new_recode.description = description
        new_recode.avatar_url = avatar_url
        new_recode.creator_id = creator_id
        new_recode.org_id = org_id
        new_recode.permission_type = permission_type
        group_id = new_recode.add_flush_commit_id()
        return group_id, new_recode


class ReUserGroup(db.Model, BaseModel):
    __tablename__ = "re_user_group"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    user_add_group_flag = db.Column(db.Boolean(), default=False, nullable=False)
    is_delete = db.Column(db.Boolean(), default=False, nullable=False)
    # 0 待加入用户；1 创建者；2 管理员；3 普通用户
    role_type = db.Column(db.Integer(), default=0, nullable=False)
    user_id = db.Column(db.String(512), db.ForeignKey('user.user_id'))
    group_id = db.Column(db.Integer(), db.ForeignKey('group.id'))
    org_id = db.Column(db.Integer(), nullable=False)

    def to_dict(self):
        _filter = [ReUserRole.user_id == self.user_id, Role.type == 'group', Role.group_id == self.group_id]
        _role = Role.query.join(ReUserRole).filter(*_filter).first()
        return {
            "id": self.id,
            "user_add_group_flag": self.user_add_group_flag,
            "is_delete": self.is_delete,
            "role_type": self.role_type,
            "user_id": self.user_id,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "role": _role.to_json() if _role else None
        }

    @staticmethod
    def create(flag, role_type, user_id, group_id, org_id):
        new_recode = ReUserGroup()
        new_recode.user_add_group_flag = flag
        new_recode.role_type = role_type
        new_recode.user_id = user_id
        new_recode.group_id = group_id
        new_recode.org_id = org_id
        new_recode.add_update()
