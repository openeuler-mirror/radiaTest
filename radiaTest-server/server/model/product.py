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

from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model.base import BaseModel, PermissionBaseModel


class Product(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(TINYTEXT())
    version_type = db.Column(
        db.Enum("LTS", "LTS-SPx", "INNOVATION"),
        nullable=False
    )
    start_time = db.Column(db.DateTime(), nullable=True)
    end_time = db.Column(db.DateTime(), nullable=True)
    is_released = db.Column(db.Boolean(), nullable=False, default=False)
    released_time = db.Column(db.DateTime(), nullable=True)
    is_forced_check = db.Column(db.Boolean(), nullable=False, default=True)
    current_resolved_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_resolved_rate = db.Column(db.String(6), nullable=True)
    current_resolved_passed = db.Column(db.Boolean(), nullable=True)
    serious_main_resolved_cnt = db.Column(
        db.Integer(), nullable=False, default=0)
    serious_main_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    serious_main_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_main_resolved_passed = db.Column(db.Boolean(), nullable=True)
    built_by_ebs = db.Column(db.Boolean(), nullable=False, default=False)

    milestone = db.relationship(
        "Milestone", backref="product", cascade="all, delete, delete-orphan"
    )
    qualityboard = db.relationship(
        "QualityBoard", backref="product", cascade="all, delete, delete-orphan"
    )
    checklist = db.relationship(
        "Checklist", backref="product", cascade="all, delete, delete-orphan"
    )
    dailybuilds = db.relationship(
        "DailyBuild", backref="product", cascade="all, delete, delete-orphan"
    )
    round = db.relationship(
        "Round", backref="product", cascade="all, delete, delete-orphan"
    )

    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "is_released": self.is_released,
            "start_time": self.convert_time_format(self.start_time),
            "end_time": self.convert_time_format(self.end_time),
            "released_time": self.convert_time_format(self.released_time),
            "version_type": self.version_type,
            "is_forced_check": self.is_forced_check,
            "serious_main_resolved_cnt": self.serious_main_resolved_cnt,
            "serious_main_all_cnt": self.serious_main_all_cnt,
            "serious_main_resolved_rate": self.serious_main_resolved_rate,
            "serious_main_resolved_passed": self.serious_main_resolved_passed,
            "current_resolved_cnt": self.current_resolved_cnt,
            "current_all_cnt": self.current_all_cnt,
            "current_resolved_rate": self.current_resolved_rate,
            "current_resolved_passed": self.current_resolved_passed,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "built_by_ebs": self.built_by_ebs
        }

