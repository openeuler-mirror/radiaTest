from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model.base import BaseModel


job_vmachine = db.Table(
    "job_vmachine",
    db.Column("job_id", db.Integer(), db.ForeignKey("job.id")),
    db.Column("vmachine_id", db.Integer(), db.ForeignKey("vmachine.id")),
)

job_physical = db.Table(
    "job_pmachine",
    db.Column("job_id", db.Integer(), db.ForeignKey("job.id")),
    db.Column("pmachine", db.Integer(), db.ForeignKey("pmachine.id")),
)

analyzed_logs = db.Table(
    "analyzed_logs",
    db.Column("analyzed_id", db.Integer(), db.ForeignKey("analyzed.id")),
    db.Column("logs_id", db.Integer(), db.ForeignKey("logs.id")),
)


class Job(BaseModel, db.Model):
    __tablename__ = "job"

    name = db.Column(db.String(512), unique=True, nullable=False)
    start_time = db.Column(db.DateTime(), nullable=False)
    end_time = db.Column(db.DateTime())
    total = db.Column(db.Integer())
    success_cases = db.Column(db.Integer())
    fail_cases = db.Column(db.Integer())
    result = db.Column(db.String(32))
    status = db.Column(db.String(32), nullable=True)
    remark = db.Column(db.String(512))
    frame = db.Column(db.String(9), nullable=False)
    master = db.Column(db.String(15))

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

    analyzeds = db.relationship('Analyzed', backref='job')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "milestone": self.milestone.to_json() if self.milestone_id else {},
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total": self.total,
            "success_cases": self.success_cases,
            "fail_cases": self.fail_cases,
            "result": self.result,
            "status": self.status,
            "remark": self.remark,
            "frame": self.frame,
            "master": self.master,
        }


class Analyzed(BaseModel, db.Model):
    __tablename__ = "analyzed"

    result = db.Column(db.String(32))
    log_url = db.Column(db.Text())
    fail_type = db.Column(db.String(32))
    details = db.Column(db.Text())
    master = db.Column(db.String(15))

    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))
    job_id = db.Column(db.Integer(), db.ForeignKey("job.id"))
    logs = db.relationship('Logs', backref='analyzed', secondary=analyzed_logs)

    def to_json(self):
        return {
            "id": self.id,
            "result": self.result,
            "log_url": self.log_url,
            "fail_type": self.fail_type,
            "details": self.details,
            "case": self.case.name,
            "job": self.job.name,
            "job_id": self.job_id,
            "create_time": self.create_time,
            "milestone_id": self.job.milestone_id,
        }

    def get_logs(self):
        data = [item.to_json() for item in self.logs]
        return data


class Logs(BaseModel, db.Model):
    __tablename__ = "logs"

    stage = db.Column(db.String(16), nullable=False)
    checkpoint = db.Column(db.String(255), nullable=False)
    expect_result = db.Column(db.Integer(), nullable=False)
    actual_result = db.Column(db.Integer(), nullable=False)
    mode = db.Column(db.Integer(), nullable=False)
    section_log = db.Column(LONGTEXT(), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "stage": self.stage,
            "checkpoint": self.checkpoint,
            "expect_result": self.expect_result,
            "actual_result": self.actual_result,
            "mode": self.mode,
            "section_log": self.section_log,
        }
