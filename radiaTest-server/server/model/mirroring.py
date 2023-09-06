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

from sqlalchemy.dialects.mysql import TINYTEXT, LONGTEXT

from server import db
from server.model.base import EmitDataModel


class IMirroring(EmitDataModel, db.Model):
    __tablename__ = "i_mirroring"

    id = db.Column(db.Integer(), primary_key=True)
    frame = db.Column(db.String(9), nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    location = db.Column(TINYTEXT())
    ks = db.Column(TINYTEXT())
    efi = db.Column(TINYTEXT())

    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    def to_json(self):
        return {
            "id": self.id,
            "frame": self.frame,
            "url": self.url,
            "location": self.location,
            "ks": self.ks,
            "efi": self.efi,
        }


class QMirroring(EmitDataModel, db.Model):
    __tablename__ = "q_mirroring"

    id = db.Column(db.Integer(), primary_key=True)
    user = db.Column(db.String(32), default="root")
    port = db.Column(db.Integer(), default=22)
    password = db.Column(db.String(256), nullable=False)

    frame = db.Column(db.String(9), nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)

    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    def to_json(self):
        return {
            "id": self.id,
            "frame": self.frame,
            "url": self.url,
            "user": self.user,
            "port": self.port,
            "password": self.password,
        }


class Repo(EmitDataModel, db.Model):
    __tablename__ = "repo"

    id = db.Column(db.Integer(), primary_key=True)
    content = db.Column(LONGTEXT(), nullable=False)
    frame = db.Column(db.String(9), nullable=False)

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

    def to_json(self):
        return {"id": self.id, "content": self.content, "frame": self.frame}
