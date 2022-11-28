import datetime
from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model import BaseModel, PermissionBaseModel


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
    round_id = db.Column(db.Integer(), db.ForeignKey("round.id"), nullable=True)

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
    test_report = db.relationship(
        "TestReport", backref="milestone", cascade="all, delete, delete-orphan"
    )

    jobs = db.relationship('Job', backref='milestone')
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        from server.model.qualityboard import Round
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
        round_info = dict()
        if self.round_id is not None:
            _round = Round.query.filter_by(id=self.round_id).first()
            if _round:
                round_info = _round.to_json()

        return {
            "id": self.id,
            "gitee_milestone_id": self.gitee_milestone_id,
            "name": self.name,
            "type": self.type,
            "start_time": self.convert_time_format(self.start_time),
            "end_time": self.convert_time_format(self.end_time),
            "product_name": self.product.name,
            "product_version": self.product.version,
            "round_id": self.round_id,
            "round_info": round_info,
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
    type = db.Column(db.Enum("milestone", "round"))
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
    gitee_milestone_id = db.Column(db.Integer())
    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id")
    )
    round_id = db.Column(
        db.Integer(), db.ForeignKey("round.id")
    )

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type,
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
            "gitee_milestone_id": self.gitee_milestone_id,
            "round_id": self.round_id
        }


class TestReport(BaseModel, db.Model):
    __tablename__ = "test_report"

    id = db.Column(db.Integer(), primary_key=True)
    md_file = db.Column(db.String(255))
    html_file = db.Column(db.String(255))
    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id")
    )

    def to_json(self):
        return {
            "id": self.id,
            "md_file": self.md_file,
            "html_file": self.html_file,
            "milestone_id": self.milestone_id,
            "milestone_name": self.milestone.name,
        }