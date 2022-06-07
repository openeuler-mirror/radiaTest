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
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        _machine_group = None
        if self.pmachine and self.pmachine.machine_group:
            _machine_group = self.pmachine.machine_group.to_json()

        return {
            "id": self.id,
            "name": self.name,
            "frame": self.frame,
            "mac": self.mac,
            "ip": self.ip,
            "password": self.password,
            "port": self.port,
            "user": self.user,
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
            "prodcut": self.product,
            "milestone": self.milestone,
            "host_ip": self.pmachine.ip,
            "host_listen": self.pmachine.listen,
            "vnc_token": self.vnc_token,
            "machine_group": _machine_group,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
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
