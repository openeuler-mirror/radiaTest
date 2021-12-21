# @Author : lemon-higgins
# @Date   : 2021-09-20 17:17:55
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model import BaseModel


class Product(BaseModel, db.Model):
    __tablename__ = "product"

    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32), nullable=False)
    description = db.Column(TINYTEXT())

    milestone = db.relationship(
        "Milestone", backref="product", cascade="all, delete, delete-orphan"
    )

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
