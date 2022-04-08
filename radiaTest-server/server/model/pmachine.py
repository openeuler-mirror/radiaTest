from datetime import datetime
from enum import unique

from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model.base import ServiceBaseModel, PermissionBaseModel



class MachineGroup(ServiceBaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "machine_group"

    ip = db.Column(db.String(15), unique=True, index=True)

    network_type = db.Column(db.Enum("WAN", "LAN"), nullable=False, default="WAN")

    messenger_last_heartbeat = db.Column(db.DateTime())
    pxe_last_heartbeat = db.Column(db.DateTime())
    dhcp_last_heartbeat = db.Column(db.DateTime())

    pmachines = db.relationship("Pmachine", backref="machine_group", cascade="all, delete, delete-orphan")
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def check_alive(self, _heartbeat):
        _current_time = datetime.now()  
        alive = False
        heartbeat = None

        if _heartbeat:
            if (_current_time - _heartbeat).seconds < 60:
                alive = True                
            
            heartbeat = _heartbeat.strftime("%Y-%m-%d %H:%M:%S")

        return alive, heartbeat

    def to_json(self):
        messenger_alive, messenger_last_heartbeat = self.check_alive(
            self.messenger_last_heartbeat
        )
        pxe_alive, pxe_last_heartbeat = self.check_alive(
            self.pxe_last_heartbeat
        )
        dhcp_alive, dhcp_last_heartbeat = self.check_alive(
            self.dhcp_last_heartbeat
        )

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "network_type": self.network_type,
            "messenger_ip": self.ip,
            "messenger_listen": self.listen,
            "messenger_alive": messenger_alive,
            "messenger_last_heartbeat": messenger_last_heartbeat,
            "pxe_alive": pxe_alive,
            "pxe_last_heartbeat": pxe_last_heartbeat,
            "dhcp_alive": dhcp_alive,
            "dhcp_last_heartbeat": dhcp_last_heartbeat,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "listen": self.listen,
            "ip": self.ip,
        }


class Pmachine(ServiceBaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "pmachine"

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
    locked = db.Column(db.Boolean(), default=False)

    machine_group_id = db.Column(db.Integer(), db.ForeignKey("machine_group.id"))

    vmachine = db.relationship(
        "Vmachine", backref="pmachine", cascade="all, delete, delete-orphan"
    )
    celerytasks = db.relationship(
        "CeleryTask", backref="pmachine", cascade="all, delete, delete-orphan"
    )
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        _start_time = None if not self.start_time else self.start_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        _end_time = None if not self.end_time else self.end_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        _boot_time = None if not self.boot_time else self.boot_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

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