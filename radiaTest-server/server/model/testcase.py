# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# Author : MDS_ZHR
# email : 331884949@qq.com
# Date : 2022/12/13 14:00:00
# License : Mulan PSL v2
#####################################
# 用例管理(Testcase)的model

from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import backref
from flask import g

from server import db
from server.model.base import BaseModel, PermissionBaseModel
from server.model.user import User
from server.model.framework import Framework, GitRepo
from server.model.group import Group
from server.model.organization import Organization
from server.model.baselinetemplate import BaselineTemplate

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
    baseline_id = db.Column(db.Integer(), db.ForeignKey("baseline.id"))

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

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
            "baseline_id": self.baseline_id,
            "is_root": self.is_root,
        }
        if self.type == 'case' and self.case_id:
            _commit = Commit.query.filter_by(
                case_detail_id=self.case_id,
                creator_id = g.user_id,
                ).order_by(
                    Commit.create_time.desc(), Commit.id.asc()
            ).first()
            if _commit:
                return_data['case_status'] = _commit.status
                return_data['commit_id'] = _commit.id
            
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

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))
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

            _framework = Framework.query.filter_by(
                id=self.git_repo.framework_id
            ).first()

            if _framework is not None:
                framework = _framework.to_json()

        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "add_network_interface": self.add_network_interface,
            "add_disk": self.add_disk,
            "remark": self.remark,
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
    version = db.Column(db.String(32))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))

    analyzeds = db.relationship('Analyzed', backref='case')

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


class Commit(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "commit"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    reviewer_id = db.Column(db.Integer())
    review_time = db.Column(db.DateTime())
    description = db.Column(db.String(255), nullable=True)
    machine_num = db.Column(db.Integer())
    machine_type = db.Column(db.String(9))
    case_description = db.Column(LONGTEXT(), nullable=False)
    preset = db.Column(LONGTEXT(), nullable=True)
    steps = db.Column(LONGTEXT(), nullable=False)
    expectation = db.Column(LONGTEXT(), nullable=False)
    remark = db.Column(LONGTEXT(), nullable=True)
    version = db.Column(db.String(32))
    status = db.Column(db.Enum("pending", "open", "accepted", "rejected"), default="pending", nullable=False)
    case_detail_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)  # 归属case
    case_mod_type = db.Column(db.Enum("add", "edit"), default="edit", nullable=False)
    source = db.Column(db.String(255))
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    comments = db.relationship("CommitComment", backref="commit", cascade="all, delete, delete-orphan")  # 评论表关联

    def to_json(self):
        reviewer_name = None
        if self.reviewer_id:
            reviewer_name = User.query.get(self.reviewer_id).user_name
        comment_count = CommitComment.query.filter_by(commit_id=self.id).count()
        _review_time = None
        if self.review_time:
            _review_time = self.review_time.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "id": self.id,
            "title": self.title,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "creator_id": self.creator_id,
            "review_time": _review_time,
            "creator": User.query.get(self.creator_id).to_dict(),
            "reviewer": User.query.get(self.reviewer_id).to_dict() if self.reviewer_id else None,
            "reviewer_name": reviewer_name,
            "description": self.description,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "case_description": self.case_description,
            "preset": self.preset,
            "steps": self.steps,
            "expectation": self.expectation,
            "remark": self.remark,
            "source": self.source,
            "status": self.status,
            "case_detail_id": self.case_detail_id,
            "case_mod_type": self.case_mod_type,
            "group_name": Group.query.get(self.group_id).name if self.group_id else None,
            "org_id": self.org_id,
            "group_id": self.group_id,
            "comment_count": comment_count,
            "org_name": Organization.query.get(self.org_id).name if self.org_id else None
        }


class CaseDetailHistory(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "case_detail_history"

    id = db.Column(db.Integer(), primary_key=True)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    machine_num = db.Column(db.Integer())
    machine_type = db.Column(db.String(9))
    case_description = db.Column(LONGTEXT(), nullable=False)
    preset = db.Column(LONGTEXT(), nullable=True)
    steps = db.Column(LONGTEXT(), nullable=False)
    expectation = db.Column(LONGTEXT(), nullable=False)
    remark = db.Column(LONGTEXT(), nullable=True)
    version = db.Column(db.String(32))
    commit_id = db.Column(db.Integer, db.ForeignKey("commit.id"), nullable=False)  # 归属commit
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "creator_id": self.creator_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": self.version,
            "creator_name": User.query.get(self.creator_id).user_name,
            "machine_num": self.machine_num,
            "machine_type": self.machine_type,
            "case_description": self.case_description,
            "preset": self.preset,
            "steps": self.steps,
            "expectation": self.expectation,
            "remark": self.remark
        }


class CommitComment(BaseModel, PermissionBaseModel, db.Model):
    """用例评审评论"""
    __tablename__ = "commit_comment"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=True)  # 内容
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    parent_id = db.Column(db.Integer(), default=0)
    commit_id = db.Column(db.Integer, db.ForeignKey("commit.id"), nullable=False)

    def to_json(self):
        user_dict = User.query.get(self.creator_id).to_dict()
        user_dict.pop('roles')
        reply_dict = None
        if self.parent_id and self.parent_id != 0:
            reply_dict = User.query.get(CommitComment.query.get(self.parent_id).creator_id).to_dict()
            reply_dict.pop('roles')
        return {
            'id': self.id,
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            'content': self.content,
            'creator_id': self.creator_id,
            'creator': user_dict,
            'parent_id': self.parent_id,
            'reply': reply_dict,
            'commit_id': self.commit_id,
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