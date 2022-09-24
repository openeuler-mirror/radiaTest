from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model.base import BaseModel, PermissionBaseModel


class Product(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(TINYTEXT())
    version_type = db.Column(
        db.Enum("LTS", "LTS-SPx", "INNOVATION"),
        nullable=False
    )
    is_forced_check = db.Column(db.Boolean(), nullable=False, default=True)
    serious_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_resolved_passed = db.Column(db.Boolean(), nullable=True)
    current_resolved_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    current_resolved_rate = db.Column(db.String(6), nullable=True)
    current_resolved_passed = db.Column(db.Boolean(), nullable=True)
    left_resolved_rate = db.Column(db.String(6), nullable=True)
    left_resolved_passed = db.Column(db.Boolean(), nullable=True)
    serious_main_resolved_cnt = db.Column(
        db.Integer(), nullable=False, default=0)
    serious_main_all_cnt = db.Column(db.Integer(), nullable=False, default=0)
    serious_main_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_main_resolved_passed = db.Column(db.Boolean(), nullable=True)
    left_issues_cnt = db.Column(db.Integer(), nullable=True, default=0)
    left_issues_passed = db.Column(db.Boolean(), nullable=True)

    milestone = db.relationship(
        "Milestone", backref="product", cascade="all, delete, delete-orphan"
    )
    qualityboard = db.relationship(
        "QualityBoard", backref="product", cascade="all, delete, delete-orphan"
    )
    dailybuilds = db.relationship(
        "DailyBuild", backref="product", cascade="all, delete, delete-orphan"
    )

    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "serious_resolved_rate": self.serious_resolved_rate,
            "serious_resolved_passed": self.serious_resolved_passed,
            "serious_main_resolved_cnt": self.serious_main_resolved_cnt,
            "serious_main_all_cnt": self.serious_main_all_cnt,
            "serious_main_resolved_rate": self.serious_main_resolved_rate,
            "serious_main_resolved_passed": self.serious_main_resolved_passed,
            "current_resolved_cnt": self.current_resolved_cnt,
            "current_all_cnt": self.current_all_cnt,
            "current_resolved_rate": self.current_resolved_rate,
            "current_resolved_passed": self.current_resolved_passed,
            "left_resolved_rate": self.current_resolved_rate,
            "left_resolved_passed": self.current_resolved_passed,
            "left_issues_cnt": self.left_issues_cnt,
            "left_issues_passed": self.left_issues_passed,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
        }
