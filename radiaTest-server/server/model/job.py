# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model import BaseModel, PermissionBaseModel

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

job_family = db.Table(
    'job_family',
    db.Column('parent_id', db.Integer, db.ForeignKey(
        'job.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey(
        'job.id'), primary_key=True)
)

class Job(BaseModel, db.Model, PermissionBaseModel):
    __tablename__ = "job"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(512), unique=True, nullable=False)
    start_time = db.Column(db.DateTime(), nullable=False)
    running_time = db.Column(db.Integer())
    end_time = db.Column(db.DateTime())
    total = db.Column(db.Integer())
    success_cases = db.Column(db.Integer())
    fail_cases = db.Column(db.Integer())
    result = db.Column(db.String(32))
    status = db.Column(db.String(32), nullable=True)
    remark = db.Column(db.String(512))
    frame = db.Column(db.String(9), nullable=False)
    master = db.Column(db.String(15))
    multiple = db.Column(db.Boolean(), nullable=False)
    is_suite_job = db.Column(db.Boolean(), default=False)
    tid = db.Column(db.String(512))

    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))

    analyzeds = db.relationship('Analyzed', backref='job')

    children = db.relationship(
        "Job",
        secondary=job_family,
        primaryjoin=(job_family.c.parent_id == id),
        secondaryjoin=(job_family.c.child_id == id),
        backref=db.backref('parent', lazy='dynamic'),
        lazy='dynamic',
        cascade="all, delete"
    )
    
    def to_dict(self):
        return self.to_json()

    def to_json(self):
        success_sum = 0
        fail_sum = 0
        masters = list()
        running_time = 0
        if self.multiple:
            for child in self.children:
                success_sum += child.success_cases
                fail_sum += child.fail_cases
                masters.append(child.master)
                running_time = max(running_time, child.running_time)

        _start_time, _end_time = None, None
        if self.start_time:
            _start_time = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        if self.end_time:
            _end_time = self.end_time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "id": self.id,
            "name": self.name,
            "milestone": self.milestone.name if self.milestone_id else None,
            "start_time": _start_time,
            "running_time": self.running_time if not self.multiple else running_time,
            "end_time": _end_time,
            "total": self.total,
            "success_cases": self.success_cases if not self.multiple else success_sum,
            "fail_cases": self.fail_cases if  not self.multiple else fail_sum,
            "result": self.result,
            "status": self.status,
            "remark": self.remark,
            "frame": self.frame,
            "master": self.master if not self.multiple else masters,
            "multiple": self.multiple,
            "tid": self.tid,
            "is_suite_job": self.is_suite_job
        }


class Analyzed(BaseModel, db.Model):
    __tablename__ = "analyzed"

    id = db.Column(db.Integer(), primary_key=True)
    result = db.Column(db.String(32))
    log_url = db.Column(db.Text())
    fail_type = db.Column(db.String(32))
    details = db.Column(db.Text())
    master = db.Column(db.String(15))
    running_time = db.Column(db.Integer())

    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))
    job_id = db.Column(db.Integer(), db.ForeignKey("job.id"))
    # 手工任务绑定
    manual_job_id = db.Column(db.Integer(), db.ForeignKey("manual_job.id"))
    logs = db.relationship('Logs', backref='analyzed', secondary=analyzed_logs)

    def to_json(self):
        milestone_id = None
        if self.job_id:
            job_name = self.job.name
            milestone_id = self.job.milestone_id
        else:
            job_name = ''
        if self.manual_job_id:
            manual_job_name = self.manual_job.name
            milestone_id = self.manual_job.milestone_id
            manual = True
        else:
            manual_job_name = ''
            manual = False

        return {
            "id": self.id,
            "result": self.result,
            "log_url": self.log_url,
            "fail_type": self.fail_type,
            "details": self.details,
            "case": self.case.to_json(),
            "job": job_name,
            "job_id": self.job_id,
            "manual_job": manual_job_name,
            "manual_job_id": self.manual_job_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "milestone_id": milestone_id,
            "running_time": self.running_time,
            "manual": manual
        }

    def get_logs(self):
        data = [item.to_json() for item in self.logs]
        return data


class Logs(BaseModel, db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer(), primary_key=True)
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


class AtJob(BaseModel, db.Model):
    __tablename__ = "at_job"
    id = db.Column(db.Integer(), primary_key=True)
    build_name = db.Column(db.String(255), nullable=False)
    at_job_name = db.Column(LONGTEXT(), nullable=True)

    def to_json(self):
        return {
            "id": self.id,
            "build_name": self.build_name,
            "at_job_name": self.at_job_name
        }