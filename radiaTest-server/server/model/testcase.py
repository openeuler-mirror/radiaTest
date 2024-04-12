# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author :
# email :
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)的model

from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model.base import BaseModel, PermissionBaseModel

case_node_family = db.Table(
    'case_node_family',
    db.Column('parent_id', db.Integer, db.ForeignKey(
        'case_node.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey(
        'case_node.id'), primary_key=True)
)


class CaseNode(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "case_node"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(64), nullable=False, default="directory")
    is_root = db.Column(db.Boolean(), default=True)
    in_set = db.Column(db.Boolean(), default=False)
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))

    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))

    suite_id = db.Column(db.Integer(), db.ForeignKey("suite.id"))

    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))
    case_result = db.Column(db.Enum('success', 'failed', 'running', "pending"), default="pending", nullable=True)
    baseline_id = db.Column(db.Integer(), db.ForeignKey("baseline.id", ondelete='CASCADE'))

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id", ondelete='CASCADE'))

    base_nodes = db.relationship("BaseNode", backref="case_node", cascade="all, delete")

    children = db.relationship(
        "CaseNode",
        secondary=case_node_family,
        primaryjoin=(case_node_family.c.parent_id == id),
        secondaryjoin=(case_node_family.c.child_id == id),
        backref=db.backref('parent', lazy='dynamic'),
        lazy='dynamic',
        cascade="all, delete"
    )

    def to_json(self):
        return_data = {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "in_set": self.in_set,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "suite_id": self.suite_id,
            "case_id": self.case_id,
            "case_result": self.case_result,
            "baseline_id": self.baseline_id,
            "is_root": self.is_root,
        }
        if self.type == 'case' and self.case_id:
            _case = Case.query.filter_by(id=self.case_id).first()
            if _case:
                return_data['case_automatic'] = _case.automatic

        return return_data

    def to_dict(self):
        _dict = self.__dict__
        _dict.update({
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        })

        return _dict


class Baseline(PermissionBaseModel, BaseModel, db.Model):
    __tablename__ = "baseline"

    id = db.Column(db.Integer(), primary_key=True)
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id", ondelete='CASCADE'))
    suite_document = db.relationship(
        "SuiteDocument", backref="baseline", cascade="all, delete, delete-orphan"
    )
    case_node = db.relationship(
        "CaseNode", backref="baseline", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        return_data = {
            "id": self.id,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "milestone_id": self.milestone_id,
        }
        return return_data


class Suite(PermissionBaseModel, BaseModel, db.Model):
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
    # 测试套来源，默认是代码仓：project，手动创建：manual
    source_type = db.Column(db.Enum("project", "manual"), nullable=False, default="project")

    git_repo_id = db.Column(db.Integer(), db.ForeignKey("git_repo.id"))

    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))

    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))

    case = db.relationship(
        "Case", backref="suite", cascade="all, delete, delete-orphan"
    )

    case_nodes = db.relationship(
        "CaseNode", backref="suite", cascade="all, delete, delete-orphan"
    )
    suite_documents = db.relationship(
        "SuiteDocument", backref="suite", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        git_repo_dict = dict()
        framework = dict()

        if self.git_repo_id:
            git_repo_dict = self.git_repo.to_json()
            framework = git_repo_dict.get("framework")

        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "add_network_interface": self.add_network_interface,
            "add_disk": self.add_disk,
            "remark": self.remark,
            "source_type": self.source_type,
            "git_repo": git_repo_dict,
            "framework": framework,
            "group_id": self.group_id,
            "org_id": self.org_id,
        }

    def relate_case_to_json(self):
        cases = list()
        if self.case:
            cases = [case_obj.relate_suite_to_json() for case_obj in self.case]
        return {
            "suite_id": self.id,
            "suite_name": self.name,
            "case": cases
        }


class Case(BaseModel, PermissionBaseModel, db.Model):
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
    description = db.Column(LONGTEXT(), nullable=True)
    preset = db.Column(LONGTEXT(), nullable=True)
    steps = db.Column(LONGTEXT(), nullable=True)
    expection = db.Column(LONGTEXT(), nullable=True)
    remark = db.Column(LONGTEXT(), nullable=True)
    owner = db.Column(db.String(64), nullable=True)
    automatic = db.Column(db.Boolean(), nullable=False, default=False)
    usabled = db.Column(db.Boolean(), nullable=False, default=False)
    code = db.Column(LONGTEXT(), nullable=True)
    deleted = db.Column(db.Boolean(), nullable=False, default=False)
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))

    case_nodes = db.relationship(
        "CaseNode", backref="case", cascade="all, delete, delete-orphan"
    )

    tasks_manuals = db.relationship(
        'TaskManualCase', backref='case', cascade='all, delete')

    def to_json(self):
        _suite = Suite.query.filter_by(id=self.suite_id).first()
        _git_repo = _suite.git_repo
        git_repo_dict = dict()

        if _git_repo is not None:
            git_repo_dict = _git_repo.to_json()

        return {
            "id": self.id,
            "name": self.name,
            "suite_id": self.suite_id,
            "suite": self.suite.name,
            "git_repo": git_repo_dict,
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
            "group_id": self.suite.group_id,
            "org_id": self.suite.org_id,
            "usabled": self.usabled,
            "code": self.code,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def relate_suite_to_json(self):
        return {
            "case_id": self.id,
            "case_name": self.name
        }


class SuiteDocument(BaseModel, db.Model):
    __tablename__ = "suite_document"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(50), nullable=False, unique=True)
    url = db.Column(db.String(512), nullable=False, unique=True)
    suite_id = db.Column(db.Integer(), db.ForeignKey("suite.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    baseline_id = db.Column(db.Integer(), db.ForeignKey("baseline.id"))
    permission_type = db.Column(db.String(50), nullable=False)

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'suite_id': self.suite_id,
            'creator_id': self.creator_id,
            "permission_type": self.permission_type,
        }


class CaseResult(BaseModel, db.Model):
    __tablename__ = "case_result"

    id = db.Column(db.Integer(), primary_key=True)
    result = db.Column(db.String(32))
    log_url = db.Column(db.Text())
    fail_type = db.Column(db.String(32))
    details = db.Column(db.Text())
    running_time = db.Column(db.Integer())
    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))
    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

    def to_json(self):
        return {
            'id': self.id,
            'result': self.result,
            'log_url': self.log_url,
            'fail_type': self.fail_type,
            'details': self.details,
            'running_time': self.running_time,
            "case_id": self.case_id,
            "milestone_id": self.milestone_id,
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }
