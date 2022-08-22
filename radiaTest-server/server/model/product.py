from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model.base import BaseModel, PermissionBaseModel


class Product(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(TINYTEXT())
    serious_resolved_rate = db.Column(db.String(6), nullable=True)
    serious_resolved_baseline = db.Column(db.String(6), nullable=True)
    current_resolved_rate = db.Column(db.String(6), nullable=True)
    current_resolved_baseline = db.Column(db.String(6), nullable=True)
    left_resolved_rate = db.Column(db.String(6), nullable=True)
    left_resolved_baseline = db.Column(db.String(6), nullable=True)
    left_issues_cnt = db.Column(db.Integer(), nullable=True, default=0)

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
            "serious_resolved_baseline": self.serious_resolved_baseline,
            "current_resolved_rate": self.current_resolved_rate,
            "current_resolved_baseline": self.current_resolved_baseline,
            "left_resolved_rate": self.current_resolved_rate,
            "left_resolved_baseline": self.current_resolved_baseline,
            "left_issues_cnt": self.left_issues_cnt,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
        }
