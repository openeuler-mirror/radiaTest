from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import backref

from server import db
from server.model import BaseModel
from server.model.framework import Framework, GitRepo


baseline_family = db.Table(
    'baseline_family',
    db.Column('parent_id', db.Integer, db.ForeignKey(
        'baseline.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey(
        'baseline.id'), primary_key=True)
)


class Baseline(BaseModel, db.Model):
    __tablename__ = "baseline"

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(64), nullable=False, default="directory")
    is_root = db.Column(db.Boolean(), default=True)
    in_set = db.Column(db.Boolean(), default=False)

    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))

    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    suite_id = db.Column(db.Integer(), db.ForeignKey("suite.id"))

    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))

    children = db.relationship(
        "Baseline",
        secondary=baseline_family,
        primaryjoin=(baseline_family.c.parent_id == id),
        secondaryjoin=(baseline_family.c.child_id == id),
        backref=db.backref('parent', lazy='dynamic'),
        lazy='dynamic',
        cascade="all, delete"
    )

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "in_set": self.in_set,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "suite_id": self.suite_id,
            "case_id": self.case_id,
        }

    def to_dict(self):
        return self.__dict__


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

    git_repo_id = db.Column(db.Integer(), db.ForeignKey("git_repo.id"))

    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))

    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    case = db.relationship(
        "Case", backref="suite", cascade="all, delete, delete-orphan"
    )

    baselines = db.relationship(
        "Baseline", backref="suite", cascade="all, delete, delete-orphan"
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
    usabled = db.Column(db.Boolean(), nullable=False, default=False)
    code = db.Column(LONGTEXT(), nullable=True)
    deleted = db.Column(db.Boolean(), nullable=False, default=False)

    analyzeds = db.relationship('Analyzed', backref='case')

    baselines = db.relationship(
        "Baseline", backref="case", cascade="all, delete, delete-orphan"
    )

    tasks_manuals = db.relationship(
        'TaskManualCase', backref='case', cascade='all, delete')

    def to_json(self):
        _git_repo = self.suite.git_repo
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
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
