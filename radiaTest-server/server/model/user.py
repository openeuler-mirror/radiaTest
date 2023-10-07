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

from flask import g
from sqlalchemy import func, select

from server.model.base import BaseModel
from server.model.permission import Role
from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.model.organization import ReUserOrganization


class User(db.Model, BaseModel):
    __tablename__ = "user"
    user_id = db.Column(db.String(512), primary_key=True)
    user_login = db.Column(db.String(50), nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True, default=None)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    cla_email = db.Column(db.String(128), nullable=True, default=None)

    like = db.Column(db.Integer(), nullable=False, default=0)
    influence = db.Column(db.Integer(), nullable=False, default=0)
    behavior = db.Column(db.Float(), nullable=False, default=100.0)

    re_user_role = db.relationship("ReUserRole", backref="user")
    re_user_group = db.relationship("ReUserGroup", backref="user")
    re_user_organization = db.relationship("ReUserOrganization", backref="user")
    re_validator_requirement_package = db.relationship("RequirementPackage", backref="validator")
    re_user_requirement_publisher = db.relationship("RequirementPublisher", backref="user")
    re_user_requirement_acceptor = db.relationship("RequirementAcceptor", backref="user")

    # 个人手机号邮箱隐私处理
    @staticmethod
    def mask_phone(phone):
        if isinstance(phone, str):
            ret = re.match(r"^1[3-9]\d{9}$", phone)
            if ret:
                return phone[:3] + "****" + phone[-4:]
        return ""

    @staticmethod
    def mask_cla_email(cla_email):
        if isinstance(cla_email, str):
            ret = re.match(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", cla_email)
            if ret:
                left, right = cla_email.split("@")
                return cla_email[0] + "*" * (len(left) - 1) + right
        return ""

    def _get_basic_info(self):
        return {
            "user_id": self.user_id,
            "user_login": self.user_login,
            "user_name": self.user_name,
            "phone": self.mask_phone(self.phone),
            "avatar_url": self.avatar_url,
            "cla_email": self.mask_phone(self.cla_email)
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

    def add_update_influence(self, table=None, namespace=None, broadcast=False):
        ranked_users = select([
            User.user_id,
            func.rank().over(
                order_by=User.influence.desc(),
                partition_by=ReUserOrganization.organization_id,
            ).label('rank')
        ]).filter(
            ReUserOrganization.is_delete == False,
            ReUserOrganization.organization_id == int(
                redis_client.hget(
                    RedisKey.user(g.user_id),
                    "current_org_id"
                )
            ),
            User.user_id == ReUserOrganization.user_id,
        )

        db.session.query(
            ReUserOrganization
        ).filter(
            ReUserOrganization.is_delete == False,
            ReUserOrganization.organization_id == int(
                redis_client.hget(
                    RedisKey.user(g.user_id),
                    "current_org_id"
                )
            ),
        ).update(
            {
                "rank": select([
                    ranked_users.c.rank
                ]).filter(
                    ranked_users.c.user_id == ReUserOrganization.user_id
                ).scalar_subquery()
            },
            synchronize_session=False
        )

        return super().add_update(table, namespace, broadcast)

    @property
    def rank(self):
        _rank = None
        org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        if self.re_user_organization and org_id is not None:
            _re = ReUserOrganization.query.filter_by(
                user_id=self.user_id,
                is_delete=False,
                organization_id=int(org_id)
            ).first()
            _rank = _re.rank
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
    #方法废弃
    def save_redis(self, access_token, refresh_token, current_org_id=None):
        redis_data = self.to_dict()
        redis_data['gitee_access_token'] = access_token
        redis_data['gitee_refresh_token'] = refresh_token
        if current_org_id:
            redis_data['current_org_id'] = current_org_id
        else:
            for item in self.re_user_organization:
                if item.default is True:
                    redis_data['current_org_id'] = item.organization_id
                    redis_data['current_org_name'] = item.organization.name
        redis_client.hmset(RedisKey.user(self.user_id), redis_data)

    @staticmethod
    def create_commit(oauth_user, cla_email=None):
        new_user = User()
        new_user.user_id = oauth_user.get("user_id")
        new_user.user_login = oauth_user.get("user_login")
        new_user.user_name = oauth_user.get("user_name")
        new_user.avatar_url = oauth_user.get("avatar_url")
        new_user.cla_email = cla_email
        new_user.add_update()
        return new_user
