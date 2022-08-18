from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model import BaseModel
from server.model.milestone import IssueSolvedRate, Milestone


class QualityBoard(BaseModel, db.Model):
    __tablename__ = "qualityboard"

    id = db.Column(db.Integer(), primary_key=True)
    iteration_version = db.Column(db.String(256), nullable=True)
    product_id = db.Column(db.Integer(), db.ForeignKey("product.id"), nullable=True)

    def get_current_version(self):
        vers = None
        if len(self.iteration_version) > 0:
            vers = self.iteration_version.split("->")[-1]
        return vers

    def get_milestones(self):
        milestones = dict()
        if len(self.iteration_version) > 0:
            mids = self.iteration_version.split("->")
            for _id in mids:
                milestone = Milestone.query.filter_by(id=_id).first()
                milestones.update({_id: milestone.to_json()})
        return milestones

    def to_json(self):
        current_milestone_id = self.get_current_version()
        _isr = IssueSolvedRate.query.filter_by(
            milestone_id=current_milestone_id
        ).first()

        return {
            "id": self.id,
            "product_id": self.product_id,
            "iteration_version": self.iteration_version,
            "milestones": self.get_milestones(),
            "current_milestone_id": current_milestone_id,
            "current_milestone_issue_solved_rate": _isr.to_json() if _isr else {},
        }


class Checklist(db.Model, BaseModel):
    __tablename__ = "checklist"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    check_item = db.Column(db.String(50), nullable=False, unique=True)
    baseline = db.Column(db.String(50))
    rounds = db.Column(db.String(128), default=False)
    lts = db.Column(db.Boolean(), default=False)
    lts_spx = db.Column(db.Boolean(), default=False)
    innovation = db.Column(db.Boolean(), default=False)

    def to_json(self):
        return {
            'id': self.id,
            'check_item': self.check_item,
            'baseline': self.baseline,
            'rounds': self.rounds,
            'lts': self.lts,
            'lts_spx': self.lts_spx,
            'innovation': self.innovation,
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            'update_time': self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }


class DailyBuild(db.Model, BaseModel):
    __tablename__ = "dailybuild"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    completion = db.Column(db.Integer(), nullable=False, default=0)
    detail = db.Column(LONGTEXT(), nullable=True)

    product_id = db.Column(db.Integer(), db.ForeignKey("product.id"))

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "completion": self.completion,
            "product_id": self.product_id
        }