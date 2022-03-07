# -*- coding: utf-8 -*-
# @Author : lemon.higgins
# @Date   : 2021-10-05 11:39:06
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2
# @Desc   :


from server import db
from server.model import BaseModel
from sqlalchemy.dialects.mysql import LONGTEXT


class Pmachine(BaseModel, db.Model):
    __tablename__ = "pmachine"

    frame = db.Column(db.String(9), nullable=False)
    mac = db.Column(db.String(17), index=True, unique=True, nullable=False)
    bmc_ip = db.Column(db.String(15), index=True, unique=True, nullable=False)
    bmc_user = db.Column(db.String(32), nullable=False)
    bmc_password = db.Column(db.String(256), nullable=False)
    ip = db.Column(db.String(15), index=True, unique=True)
    user = db.Column(db.String(32), default="root")
    port = db.Column(db.Integer(), default=22)
    password = db.Column(db.String(256))
    description = db.Column(db.String(256))
    listen = db.Column(db.Integer())
    start_time = db.Column(db.DateTime())
    end_time = db.Column(db.DateTime())
    boot_time = db.Column(db.DateTime())
    state = db.Column(db.String(9), default="idle")
    filename = db.Column(LONGTEXT())
    status = db.Column(db.String(9))
    occupier = db.Column(db.String(64), nullable=True)
    locked = db.Column(db.Boolean(), default=False)

    vmachine = db.relationship(
        "Vmachine", backref="pmachine", cascade="all, delete, delete-orphan"
    )
    celerytasks = db.relationship(
        "CeleryTask", backref="pmachine", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        return {
            "id": self.id,
            "frame": self.frame,
            "mac": self.mac,
            "bmc_ip": self.bmc_ip,
            "bmc_user": self.bmc_user,
            "bmc_password": self.bmc_password,
            "ip": self.ip,
            "user": self.user,
            "password": self.password,
            "port": self.port,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "state": self.state,
            "listen": self.listen,
            "status": self.status,
            "occupier": self.occupier,
            "locked": self.locked,
        }
