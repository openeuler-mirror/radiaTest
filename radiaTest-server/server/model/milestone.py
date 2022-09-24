import datetime
from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model import BaseModel, PermissionBaseModel


class MilestoneGroup(db.Model, BaseModel):
    __tablename__ = "milestone_group"

    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    milestone_1_id = db.Column(
        db.Integer(), db.ForeignKey('milestone.id', ondelete="CASCADE"), primary_key=True
    )
    milestone_2_id = db.Column(
        db.Integer(), db.ForeignKey('milestone.id', ondelete="CASCADE"), primary_key=True
    )


class Milestone(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "milestone"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(9), nullable=False)
    start_time = db.Column(db.Date(), nullable=False)
    end_time = db.Column(db.Date(), nullable=False)
    description = db.Column(TINYTEXT())
    state = db.Column(db.Enum("active", "closed"), default="active")
    is_sync = db.Column(db.Boolean(), default=False)
    gitee_milestone_id = db.Column(db.Integer(), nullable=True)

    product_id = db.Column(db.Integer(), db.ForeignKey("product.id"))

    imirroring = db.relationship(
        "IMirroring", backref="milestone", cascade="all, delete, delete-orphan"
    )
    qmirroring = db.relationship(
        "QMirroring", backref="milestone", cascade="all, delete, delete-orphan"
    )
    repo = db.relationship(
        "Repo", backref="milestone", cascade="all, delete, delete-orphan"
    )
    template = db.relationship(
        "Template", backref="milestone", cascade="all, delete, delete-orphan"
    )
    tasks = db.relationship('TaskMilestone', backref='milestone')
    issue_solved_rate = db.relationship(
        "IssueSolvedRate", backref="milestone", cascade="all, delete, delete-orphan"
    )

    jobs = db.relationship('Job', backref='milestone')
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def convert_time_format(self, t):
        if isinstance(t, datetime.date):
            return t.strftime("%Y-%m-%d")
        else:
            return t

    def to_json(self):
        tags = []
        for mirroring in self.imirroring:
            if mirroring.frame == "x86_64":
                tags.append("x86_64-iso")
            if mirroring.frame == "aarch64":
                tags.append("aarch64-iso")
        for mirroring in self.qmirroring:
            if mirroring.frame == "x86_64":
                tags.append("x86_64-qcow2")
            if mirroring.frame == "aarch64":
                tags.append("aarch64-qcow2")
        for rep in self.repo:
            if rep.frame == "x86_64":
                tags.append("x86_64-repo")
            if rep.frame == "aarch64":
                tags.append("aarch64-repo")

        return {
            "id": self.id,
            "gitee_milestone_id": self.gitee_milestone_id,
            "name": self.name,
            "type": self.type,
            "start_time": self.convert_time_format(self.start_time),
            "end_time": self.convert_time_format(self.end_time),
            "product_name": self.product.name,
            "product_version": self.product.version,
            "tags": tags,
            "task_num": len(self.tasks),
            "state": self.state,
            "is_sync": self.is_sync,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
        }


class IssueSolvedRate(BaseModel, db.Model):
    __tablename__ = "issue_solved_rate"

    id = db.Column(db.Integer(), primary_key=True)
    serious_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_resolved_passed = db.Column(db.Boolean(), nullable=True)
    main_resolved_rate = db.Column(db.String(6), nullable=True)
    main_resolved_passed = db.Column(db.Boolean(), nullable=True)
    serious_main_resolved_cnt = db.Column(
        db.Integer(), nullable=False, default=0)
    serious_main_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    serious_main_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_main_resolved_passed = db.Column(db.Boolean(), nullable=True)
    current_resolved_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_resolved_rate = db.Column(db.String(6), nullable=True)
    current_resolved_passed = db.Column(db.Boolean(), nullable=True)
    left_issues_cnt = db.Column(db.Integer(), nullable=False, default=0)
    left_issues_passed = db.Column(db.Boolean(), nullable=True)
    invalid_issues_cnt = db.Column(db.Integer(), nullable=False, default=0)
    invalid_issues_passed = db.Column(db.Boolean(), nullable=True)
    previous_left_resolved_rate = db.Column(db.String(6), nullable=True)
    gitee_milestone_id = db.Column(db.Integer(), nullable=False)
    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    def to_json(self):
        return {
            "id": self.id,
            "serious_resolved_rate": self.serious_resolved_rate,
            "serious_resolved_passed": self.serious_resolved_passed,
            "main_resolved_rate": self.main_resolved_rate,
            "main_resolved_passed": self.main_resolved_passed,
            "serious_main_resolved_cnt": self.serious_main_resolved_cnt,
            "serious_main_all_cnt": self.serious_main_all_cnt,
            "serious_main_resolved_rate": self.serious_main_resolved_rate,
            "serious_main_resolved_passed": self.serious_main_resolved_passed,
            "current_resolved_cnt": self.current_resolved_cnt,
            "current_all_cnt": self.current_all_cnt,
            "current_resolved_rate": self.current_resolved_rate,
            "current_resolved_passed": self.current_resolved_passed,
            "left_issues_cnt": self.left_issues_cnt,
            "left_issues_passed": self.left_issues_passed,
            "invalid_issues_cnt": self.invalid_issues_cnt,
            "invalid_issues_passed": self.invalid_issues_passed,
            "previous_left_resolved_rate": self.previous_left_resolved_rate,
            "milestone_id": self.milestone_id,
            "gitee_milestone_id": self.gitee_milestone_id
        }
