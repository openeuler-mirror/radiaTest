# -*- coding: utf-8 -*-
# @Author : Ethan-Zhang
# @Date   : 2021-09-10 14:31:00
# @Email  : ethanzhang55@outlook.com
# @License: Mulan PSL v2
# @Desc   :


import json

from server import db
from server.model import BaseModel
from server.model.milestone import Milestone
from sqlalchemy.dialects.mysql import LONGTEXT
from server.model.testcase import Case


template_case = db.Table(
    "template_case",
    db.Column("template_id", db.Integer(), db.ForeignKey("template.id")),
    db.Column("case_id", db.Integer(), db.ForeignKey("case.id")),
)


class Template(BaseModel, db.Model):
    __tablename__ = "template"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(LONGTEXT(), nullable=True)
    author = db.Column(db.String(32))
    owner = db.Column(db.String(32))
    template_type = db.Column(db.String(32))

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

    def _get_cases_name(self):
        cases_name = []
        for case in self.cases:
            cases_name.append(Case.query.filter_by(id=case.id).first().name)
        return cases_name

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "milestone": Milestone.query.filter_by(id=self.milestone_id).first().name,
            "git_repo": self.git_repo.to_json() if self.git_repo_id else {},
            "cases": self._get_cases_name(),
            "author": self.author,
            "owner": self.owner,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "template_type": self.template_type,
        }
