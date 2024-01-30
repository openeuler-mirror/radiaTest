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

from server import db
from server.model import BaseModel, PermissionBaseModel


class Framework(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "framework"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    logs_path = db.Column(db.String(256))
    adaptive = db.Column(db.Boolean(), nullable=False, default=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    git_repos = db.relationship('GitRepo', backref='framework')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "logs_path": self.logs_path,
            "adaptive": self.adaptive,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class GitRepo(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "git_repo"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    git_url = db.Column(db.String(256), nullable=False)
    branch = db.Column(db.String(64), nullable=False, default="master")
    sync_rule = db.Column(db.Boolean(), nullable=False, default=True)
    adaptive = db.Column(db.Boolean(), nullable=False, default=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    framework_id = db.Column(db.Integer(), db.ForeignKey("framework.id"))

    suites = db.relationship('Suite', backref='git_repo')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "git_url": self.git_url,
            "branch": self.branch,
            "sync_rule": self.sync_rule,
            "adaptive": self.adaptive,
            "framework": self.framework.to_json(),
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
        }
