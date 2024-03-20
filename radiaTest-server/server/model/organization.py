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
from enum import Enum

from server import db
from server.model import BaseModel, PermissionBaseModel


class OrganizationRole(Enum):
    admin = 2
    user = 0


class Organization(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "organization"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)

    authority = db.Column(db.String(50), nullable=False)
    enterprise_id = db.Column(db.String(50))
    enterprise_token = db.Column(db.String(512))
    enterprise_join_url = db.Column(db.String(512))
    oauth_login_url = db.Column(db.String(512), nullable=False)
    oauth_get_token_url = db.Column(db.String(512), nullable=False)
    oauth_get_user_info_url = db.Column(db.String(512), nullable=False)
    oauth_client_id = db.Column(db.String(512), nullable=False)
    oauth_client_secret = db.Column(db.String(512), nullable=False)
    oauth_scope = db.Column(db.String(512), nullable=False)
    roles = db.relationship("Role", cascade="all, delete", backref="organization")

    re_org_publisher = db.relationship("RequirementPublisher", backref="org")

    @staticmethod
    def create(model):
        new_recode = Organization()
        new_recode.name = model.name
        new_recode.avatar_url = model.avatar_url
        new_recode.description = model.description
        new_recode.enterprise_id = model.enterprise_id
        new_recode.enterprise_join_url = model.enterprise_join_url
        new_recode.oauth_client_id = model.oauth_client_id
        new_recode.oauth_client_secret = model.oauth_client_secret
        new_recode.oauth_scope = model.oauth_scope
        new_recode.authority = model.authority
        new_recode.oauth_login_url = model.oauth_login_url
        new_recode.oauth_get_token_url = model.oauth_get_token_url
        new_recode.oauth_get_user_info_url = model.oauth_get_user_info_url
        new_id = new_recode.add_flush_commit_id()
        if not new_id:
            return None
        new_recode.id = new_id
        return new_recode

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

    def to_dict(self):
        _dict = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "avatar_url": self.avatar_url,
            "is_delete": self.is_delete,
            "enterprise_id": self.enterprise_id,
            "enterprise_token": self.enterprise_token,
            "enterprise_join_url": self.enterprise_join_url,
            "oauth_client_id": self.oauth_client_id,
            "oauth_scope": self.oauth_scope,
            "oauth_client_secret": self.oauth_client_secret,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "authority": self.authority,
            "oauth_login_url": self.oauth_login_url,
            "oauth_get_token_url": self.oauth_get_token_url,
            "oauth_get_user_info_url": self.oauth_get_user_info_url,
        }

        return _dict

    def to_summary(self):
        return {
            "name": self.name,
            "description": self.description,
            "avatar_url": self.avatar_url,
        }
