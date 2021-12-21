# @Author : lemon-higgins
# @Date   : 2021-10-02 10:41:01
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from sqlalchemy.dialects.mysql import TINYTEXT

from server import db
from server.model import BaseModel
from server.model.task import TaskMilestone


class Milestone(BaseModel, db.Model):
    __tablename__ = "milestone"

    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(9), nullable=False)
    start_time = db.Column(db.Date(), nullable=False)
    end_time = db.Column(db.Date(), nullable=False)
    description = db.Column(TINYTEXT())

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

    jobs = db.relationship('Job', backref='milestone')

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
            "name": self.name,
            "type": self.type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "product_name": self.product.name,
            "product_version": self.product.version,
            "tags": tags,
            "task_num": len(self.tasks),
        }

