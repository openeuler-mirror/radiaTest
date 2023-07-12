# -*- coding: utf-8 -*-
# @Author: Your name
# @Date:   2022-04-12 11:23:44
import os
from datetime import datetime
from enum import unique

from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model.base import EmitDataModel, ServiceModel, PermissionBaseModel



class MachineGroup(EmitDataModel, PermissionBaseModel, db.Model):
    __tablename__ = "machine_group"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(256))
    ip = db.Column(db.String(15), unique=True, index=True)

    network_type = db.Column(db.Enum("WAN", "LAN"), nullable=False, default="WAN")

    messenger_ip = db.Column(db.String(15))
    messenger_listen = db.Column(db.Integer(), nullable=False)

    websockify_ip = db.Column(db.String(15))
    websockify_listen = db.Column(db.Integer(), nullable=False)

    messenger_alive = db.Column(db.Boolean(), nullable=False, default=False)
    pxe_alive = db.Column(db.Boolean(), nullable=False, default=False)
    dhcp_alive = db.Column(db.Boolean(), nullable=False, default=False)
    messenger_last_heartbeat = db.Column(db.DateTime())
    pxe_last_heartbeat = db.Column(db.DateTime())
    dhcp_last_heartbeat = db.Column(db.DateTime())

    pmachines = db.relationship("Pmachine", backref="machine_group", cascade="all, delete, delete-orphan")

    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def _change_format(self, last_heartbeat):
        if isinstance(last_heartbeat, datetime):
            return last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ip": self.ip,
            "network_type": self.network_type,
            "messenger_ip": self.messenger_ip,
            "messenger_listen": self.messenger_listen,
            "websockify_ip": self.websockify_ip,
            "websockify_listen": self.websockify_listen,
            "messenger_alive": self.messenger_alive,
            "pxe_alive": self.pxe_alive,
            "dhcp_alive": self.dhcp_alive,
            "messenger_last_heartbeat": self._change_format(self.messenger_last_heartbeat),
            "pxe_last_heartbeat": self._change_format(self.pxe_last_heartbeat),
            "dhcp_last_heartbeat": self._change_format(self.dhcp_last_heartbeat),
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
        }


class Pmachine(ServiceModel, PermissionBaseModel, db.Model):
    __tablename__ = "pmachine"

    id = db.Column(db.Integer(), primary_key=True)
    frame = db.Column(db.String(9), nullable=False)
    mac = db.Column(db.String(17), index=True, unique=True, nullable=False)
    bmc_ip = db.Column(db.String(15), index=True, unique=True, nullable=False)
    bmc_user = db.Column(db.String(32), nullable=False)
    bmc_password = db.Column(db.String(256), nullable=False)
    user = db.Column(db.String(32), default="root")
    port = db.Column(db.Integer(), default=22)
    password = db.Column(db.String(256))
    start_time = db.Column(db.DateTime())
    end_time = db.Column(db.DateTime())
    boot_time = db.Column(db.DateTime())
    state = db.Column(db.String(9), default="idle")
    filename = db.Column(LONGTEXT())
    status = db.Column(db.String(9))
    occupier = db.Column(db.String(64), nullable=True)
    occupier_id = db.Column(db.String(512), nullable=True)
    locked = db.Column(db.Boolean(), default=False)
    is_release_notification = db.Column(db.Boolean(), nullable=False, default=False)
    machine_group_id = db.Column(db.Integer(), db.ForeignKey("machine_group.id"))

    vmachine = db.relationship(
        "Vmachine", backref="pmachine", cascade="all, delete, delete-orphan"
    )
    celerytasks = db.relationship(
        "CeleryTask", backref="pmachine", cascade="all, delete, delete-orphan"
    )
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def standardize_time(self):
        _start_time = None if not self.start_time else self.start_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        _end_time = None if not self.end_time else self.end_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        _boot_time = None if not self.boot_time else self.boot_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return _start_time, _end_time, _boot_time

    def to_public_json(self):
        _start_time, _end_time, _boot_time = self.standardize_time()

        return {
            "id": self.id,
            "frame": self.frame,
            "ip": self.ip,
            "port": self.port,
            "mac": self.mac,
            "bmc_ip": self.bmc_ip,
            "description": self.description,
            "start_time": _start_time,
            "end_time": _end_time,
            "boot_time": _boot_time,
            "state": self.state,
            "listen": self.listen,
            "status": self.status,
            "occupier": self.occupier,
            "locked": self.locked,
            "machine_group": self.machine_group.to_json() if self.machine_group_id else None,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
        }

    def to_bmc_json(self):
        return {
            "bmc_user": self.bmc_user,
            "bmc_password": self.bmc_password,         
        }
    
    def to_ssh_json(self):
        return {
            "user": self.user,
            "password": self.password,
        }

    def to_json(self):
        return_dict = {
            **self.to_public_json(),
            **self.to_bmc_json(),
            **self.to_ssh_json()
        }
        return return_dict

