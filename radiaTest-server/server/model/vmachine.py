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
from server.model.base import EmitDataModel


class Vmachine(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "vmachine"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    frame = db.Column(db.String(10), nullable=False)
    mac = db.Column(db.String(48), unique=True)
    ip = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(255), nullable=False, default="openEuler12#$")
    port = db.Column(db.Integer(), nullable=False, default=22)
    user = db.Column(db.String(32), nullable=False, default="root")
    sockets = db.Column(db.Integer(), nullable=False)
    cores = db.Column(db.Integer(), nullable=False)
    threads = db.Column(db.Integer(), nullable=False)
    cpu_mode = db.Column(db.String(32), nullable=False)
    memory = db.Column(db.Integer(), nullable=False)
    vnc_port = db.Column(db.Integer())
    status = db.Column(db.String(32), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    end_time = db.Column(db.DateTime(), nullable=False)
    special_device = db.Column(db.String(128))

    vnc_token = db.Column(db.String(255))

    product = db.Column(db.String(64), nullable=False)
    milestone = db.Column(db.String(64), nullable=False)
    is_release_notification = db.Column(db.Boolean(), nullable=False, default=False)
    pmachine_id = db.Column(db.Integer(), db.ForeignKey("pmachine.id"))

    vnic = db.relationship(
        "Vnic", backref="vmachine", cascade="all, delete, delete-orphan"
    )
    disk = db.relationship(
        "Vdisk", backref="vmachine", cascade="all, delete, delete-orphan"
    )
    celerytasks = db.relationship(
        "CeleryTask", backref="vmachine", cascade="all, delete, delete-orphan"
    )
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_public_json(self):
        _machine_group = None
        if self.pmachine and self.pmachine.machine_group:
            _machine_group = self.pmachine.machine_group.to_json()

        return {
            "id": self.id,
            "name": self.name,
            "frame": self.frame,
            "mac": self.mac,
            "ip": self.ip,
            "port": self.port,
            "sockets": self.sockets,
            "cores": self.cores,
            "threads": self.threads,
            "cpu_mode": self.cpu_mode,
            "memory": self.memory,
            "vnc_port": self.vnc_port,
            "status": self.status,
            "description": self.description,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "special_device": self.special_device,
            "product": self.product,
            "milestone": self.milestone,
            "host_id": self.pmachine_id,
            "host_ip": self.pmachine.ip,
            "host_listen": self.pmachine.listen,
            "vnc_token": self.vnc_token,
            "machine_group": _machine_group,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "is_release_notification": self.is_release_notification
        }

    def to_ssh_json(self):
        return {
            "password": self.password,
            "user": self.user,
        }

    def to_json(self):
        return {
            **self.to_public_json(),
            **self.to_ssh_json()
        }


class Vnic(EmitDataModel, db.Model):
    __tablename__ = "vnic"

    id = db.Column(db.Integer(), primary_key=True)
    mode = db.Column(db.String(9), nullable=False)
    source = db.Column(db.String(16), nullable=False)
    bus = db.Column(db.String(9), nullable=False)
    mac = db.Column(db.String(48), unique=True, nullable=False)

    vmachine_id = db.Column(db.Integer(), db.ForeignKey("vmachine.id"))

    def to_json(self):
        return {
            "id": self.id,
            "bus": self.bus,
            "mode": self.mode,
            "mac": self.mac,
            "source": self.source,
            "vmachine_id": self.vmachine_id,
        }


class Vdisk(EmitDataModel, db.Model):
    __tablename__ = "vdisk"

    id = db.Column(db.Integer(), primary_key=True)
    bus = db.Column(db.String(16), nullable=False)
    capacity = db.Column(db.Integer(), nullable=False)
    cache = db.Column(db.String(16), nullable=False, default="default")
    volume = db.Column(db.String(256), nullable=False)

    vmachine_id = db.Column(db.Integer(), db.ForeignKey("vmachine.id"))

    def to_json(self):
        return {
            "id": self.id,
            "bus": self.bus,
            "capacity": self.capacity,
            "cache": self.cache,
            "volume": self.volume,
            "vmachine_id": self.vmachine_id,
        }
