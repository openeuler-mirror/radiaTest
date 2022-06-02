from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model.base import BaseModel, PermissionBaseModel


class Product(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(TINYTEXT())

    milestone = db.relationship(
        "Milestone", backref="product", cascade="all, delete, delete-orphan"
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
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id
        }
