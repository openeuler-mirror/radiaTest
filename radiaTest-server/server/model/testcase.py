# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-06 20:39:53
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :

from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model import BaseModel


class Suite(BaseModel, db.Model):
    __tablename__ = "suite"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    machine_num = db.Column(db.Integer())
    machine_type = db.Column(db.String(9))
    add_network_interface = db.Column(db.Integer())
    add_disk = db.Column(db.String(64))
    remark = db.Column(LONGTEXT(), nullable=True)
    owner = db.Column(db.String(64), nullable=True)
    deleted = db.Column(db.Boolean(), nullable=False, default=False)

    case = db.relationship(
        "Case", backref="suite", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "add_network_interface": self.add_network_interface,
            "add_disk": self.add_disk,
            "remark": self.remark,
        }


class Case(BaseModel, db.Model):
    __tablename__ = "case"

    id = db.Column(db.Integer(), primary_key=True)
    suite_id = db.Column(db.Integer(), db.ForeignKey("suite.id"))
    name = db.Column(db.String(255), nullable=False, unique=True)
    test_level = db.Column(db.String(255), nullable=True)
    test_type = db.Column(db.String(255), nullable=True)
    machine_num = db.Column(db.Integer(), default=1)
    machine_type = db.Column(db.String(9), default="kvm")
    add_network_interface = db.Column(db.Integer(), nullable=True)
    add_disk = db.Column(db.String(64), nullable=True)
    description = db.Column(LONGTEXT(), nullable=False)
    preset = db.Column(LONGTEXT(), nullable=True)
    steps = db.Column(LONGTEXT(), nullable=False)
    expection = db.Column(LONGTEXT(), nullable=False)
    remark = db.Column(LONGTEXT(), nullable=True)
    owner = db.Column(db.String(64), nullable=True)
    automatic = db.Column(db.Boolean(), nullable=False, default=False)
    deleted = db.Column(db.Boolean(), nullable=False, default=False)

    analyzeds = db.relationship('Analyzed', backref='case')

    tasks_manuals = db.relationship('TaskManualCase', backref='case', cascade='all, delete')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "suite_id": self.suite_id,
            "suite": self.suite.name,
            "test_level": self.test_level,
            "test_type": self.test_type,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "add_network_interface": self.add_network_interface,
            "add_disk": self.add_disk,
            "description": self.description,
            "preset": self.preset,
            "steps": self.steps,
            "expection": self.expection,
            "remark": self.remark,
            "owner": self.owner,
            "automatic": self.automatic,
            "deleted": self.deleted,
        }
