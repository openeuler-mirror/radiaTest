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
import re

from server.model.base import BaseModel
from server.model.permission import Role
from server import db


class User(db.Model, BaseModel):
    __tablename__ = "user"
    user_id = db.Column(db.String(512), primary_key=True)
    user_login = db.Column(db.String(50), nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)

    like = db.Column(db.Integer(), nullable=False, default=0)
    influence = db.Column(db.Integer(), nullable=False, default=0)
    behavior = db.Column(db.Float(), nullable=False, default=100.0)
    org_id = db.Column(db.Integer(), nullable=False, default=0)

    re_user_role = db.relationship("ReUserRole", backref="user")
    re_user_group = db.relationship("ReUserGroup", backref="user")
    re_validator_requirement_package = db.relationship("RequirementPackage", backref="validator")
    re_user_requirement_publisher = db.relationship("RequirementPublisher", backref="user")
    re_user_requirement_acceptor = db.relationship("RequirementAcceptor", backref="user")

    def _get_basic_info(self):
        return {
            "user_id": self.user_id,
            "user_login": self.user_login,
            "user_name": self.user_name,
            "avatar_url": self.avatar_url
        }

    def _get_roles(self):
        roles = []
        for re in self.re_user_role:
            role = Role.query.filter_by(id=re.role_id).first()
            roles.append(role.to_json())
        return roles

    def _get_public_role(self):
        from server.model.permission import Role, ReUserRole
        _filter = [ReUserRole.user_id == self.user_id, Role.type == 'public']
        _role = Role.query.join(ReUserRole).filter(*_filter).first()
        return _role.to_json() if _role else None

    @property
    def rank(self):
        _rank = None
        return _rank

    def to_summary(self):
        return {
            **self._get_basic_info(),
            "influence": self.influence,
            "behavior": self.behavior,
            "like": self.like,
            "rank": self.rank,
        }

    def to_dict(self):
        return {
            **self._get_basic_info(),
            "roles": self._get_roles()
        }

    def to_json(self):
        return {
            **self._get_basic_info(),
            "roles": self._get_roles(),
            "role": self._get_public_role(),
            "influence": self.influence,
            "behavior": self.behavior,
            "like": self.like,
            "rank": self.rank,
        }

    @staticmethod
    def synchronize_oauth_info(oauth_user, user=None):
        user.user_login = oauth_user.get("user_login")
        user.user_name = oauth_user.get("user_name")
        user.avatar_url = oauth_user.get("avatar_url")
        user.add_update()
        return user

    @staticmethod
    def create_commit(oauth_user, org_id):
        new_user = User()
        new_user.user_id = oauth_user.get("user_id")
        new_user.user_login = oauth_user.get("user_login")
        new_user.user_name = oauth_user.get("user_name")
        new_user.avatar_url = oauth_user.get("avatar_url")
        new_user.org_id = org_id
        new_user.add_update()
        return new_user
