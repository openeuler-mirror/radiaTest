# @Author : lemon-higgins
# @Date   : 2021-10-04 10:15:46
# @Email  :
# @License:
# @Desc   :


from sqlalchemy.dialects.mysql import TINYTEXT, LONGTEXT

from server import db
from server.model import BaseModel


class IMirroring(BaseModel, db.Model):
    __tablename__ = "i_mirroring"

    frame = db.Column(db.String(9), nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    location = db.Column(TINYTEXT())
    ks = db.Column(TINYTEXT())
    efi = db.Column(TINYTEXT())

    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    def to_json(self):
        return {
            "id": self.id,
            "frame": self.frame,
            "url": self.url,
            "location": self.location,
            "ks": self.ks,
            "efi": self.efi,
        }


class QMirroring(BaseModel, db.Model):
    __tablename__ = "q_mirroring"

    user = db.Column(db.String(32), default="root")
    port = db.Column(db.Integer(), default=22)
    password = db.Column(db.String(256), nullable=False)

    frame = db.Column(db.String(9), nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)

    milestone_id = db.Column(
        db.Integer(), db.ForeignKey("milestone.id"), nullable=False
    )

    def to_json(self):
        return {
            "id": self.id,
            "frame": self.frame,
            "url": self.url,
            "user": self.user,
            "port": self.port,
            "password": self.password,
        }


class Repo(BaseModel, db.Model):
    __tablename__ = "repo"

    content = db.Column(LONGTEXT(), nullable=False)
    frame = db.Column(db.String(9), nullable=False)

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

    def to_json(self):
        return {"id": self.id, "content": self.content, "frame": self.frame}
