from sqlalchemy.dialects.mysql import TINYTEXT

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
