from server import db
from server.model.base import BaseModel, PermissionBaseModel
from server.model.milestone import Milestone
from server.model.user import User
from server.model.group import Group
from server.model.organization import Organization
from sqlalchemy.dialects.mysql import LONGTEXT


template_case = db.Table(
    "template_case",
    db.Column("template_id", db.Integer(), db.ForeignKey("template.id")),
    db.Column("case_id", db.Integer(), db.ForeignKey("case.id")),
)


class Template(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "template"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(LONGTEXT(), nullable=True)

    cases = db.relationship(
        "Case",
        secondary=template_case,
        backref="templates",
    )

    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    git_repo_id = db.Column(
        db.Integer(), db.ForeignKey("git_repo.id"), nullable=False
    )

    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        author = User.query.filter_by(gitee_id=self.creator_id).first().gitee_name
        if self.permission_type == "person":
            owner = User.query.filter_by(gitee_id=self.creator_id).first().gitee_name
        elif self.permission_type == "group":
            owner = Group.query.filter_by(id=self.group_id).first().name
        elif self.permission_type == "org":
            owner = Organization.query.filter_by(id=self.org_id).first().name
        elif self.permission_type == "public":
            owner = "public"

        suite_cases = dict()
        for case in self.cases:
            if suite_cases.get(case.suite.name):
                suite_cases.get(case.suite.name).get("cases").append(case.to_json())
            else:
                suite_cases.update(
                    {
                        case.suite.name: {
                            "suite": case.suite.name,
                            "cases": [case.to_json()],
                        }
                    }
                )

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "milestone": Milestone.query.filter_by(id=self.milestone_id).first().name,
            "milestone_id": self.milestone_id,
            "git_repo": self.git_repo.to_json() if self.git_repo_id else {},
            "cases": [case.to_json() for case in self.cases],
            "suite_cases": suite_cases,
            "author": author,
            "owner": owner,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "template_type": self.permission_type,
            "creator_id": self.creator_id,
            "group_id": self.group_id,
            "org_id": self.org_id
        }
