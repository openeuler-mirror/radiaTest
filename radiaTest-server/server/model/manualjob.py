# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author : 董霖峰
# @email : 1063183942@qq.com
# @Date : 2022/12/05 16:43:43
# @License : Mulan PSL v2
#####################################
# 手工测试任务(ManualJob)相关表的定义
#
#   +----+       +----------+       +---------------+
#   |case|<------|manual_job|<------|manual_job_step|
#   +----+ 1   n +----------+ 1   n +---------------+

from datetime import datetime
from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model import PermissionBaseModel
from server.model.base import BaseModel
from server.model.user import User
from server.model.milestone import Milestone
from server.model.testcase import Case


class ManualJobGroup(BaseModel, db.Model, PermissionBaseModel):
    __tablename__ = "manual_job_group"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    # 无法进行迁移，进行逻辑关联
    creator_id = db.Column(db.String(512))
    milestone_id = db.Column(db.Integer())
    group_id = db.Column(db.Integer())
    org_id = db.Column(db.Integer())
    status = db.Column(db.Integer, nullable=False, default=0)  # 0: In progress, 1: Completed.
    report = db.Column(LONGTEXT(), nullable=True)  # 富文本报告

    def to_json(self):
        success = 0
        failed = 0
        block = 0
        progress = 0
        manual_jobs = ManualJob.query.filter_by(job_group_id=self.id).all()
        for job in manual_jobs:
            # 用例任务执行完成
            if job.status == 1:
                # 结果一致则用例执行通过
                if job.result == 1:
                    success += 1
                elif job.result == 2:
                    block += 1
                else:
                    failed += 1
            else:
                progress += 1
        milestone_name = ''
        if self.milestone_id:
            milestone = Milestone.query.filter_by(id=self.milestone_id).first()
            if milestone:
                milestone_name = milestone.name

        return {
            "id": self.id,
            "name": self.name,
            "creator_id": self.creator_id,
            "milestone_id": self.milestone_id,
            "milestone": milestone_name,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "status": self.status,
            "total": len(manual_jobs),
            "success": success,
            "failed": failed,
            "progress": progress,
            "block": block,
            "report": self.report,
            "update_time": self.update_time,
            "create_time": self.create_time,
            # 状态描述信息
            "status_desc": {
                "total": "所有",
                "success": "成功",
                "failed": "失败",
                "progress": "执行中",
                "block": "阻塞",
            }}

    def to_statist(self):
        statist_dict = self.to_json()
        all_jobs = []
        success_jobs = []
        failed_jobs = []
        progress_jobs = []
        block_jobs = []
        manual_jobs = ManualJob.query.filter_by(job_group_id=self.id).all()
        for job in manual_jobs:
            all_jobs.append(job.to_json())
            # 用例任务执行完成
            if job.status == 1:
                # 结果一致则用例执行通过
                if job.result == 1:
                    success_jobs.append(job.to_json())
                elif job.result == 2:
                    block_jobs.append(job.to_json())
                else:
                    failed_jobs.append(job.to_json())
            else:
                progress_jobs.append(job.to_json())

        statist_dict.update({
            "all_jobs": all_jobs,
            "success_jobs": success_jobs,
            "failed_jobs": failed_jobs,
            "progress_jobs": progress_jobs,
            "block_jobs": block_jobs,
        })
        # 若状态为已完成，则统计完成率和通过率

        if self.status == 1:
            statist_dict.update({
                "finished_rate": "{:.0%}".format((statist_dict["total"] - statist_dict["progress"]) /
                                                 statist_dict["total"]),
                "success_rate": "{:.0%}".format(statist_dict["success"]/statist_dict["total"]),
            })
            statist_dict["status_desc"]["progress"] = "未完成"

        return statist_dict


class ManualJob(BaseModel, db.Model, PermissionBaseModel):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    start_time = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    end_time = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    # With expectation, -1: 表示存在一些步骤的日志未填写 0: Inconsistent, 1: Consistent. 2：block
    result = db.Column(db.Integer(), nullable=False, default=0)
    current_step = db.Column(db.Integer(), nullable=False, default=0)
    total_step = db.Column(db.Integer(), nullable=False)

    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))
    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))

    job_group_id = db.Column(db.Integer())  # 无法进行迁移，进行逻辑关联
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    status = db.Column(db.Integer, nullable=False, default=0)  # 0: In progress, 1: Completed.
    remark = db.Column(LONGTEXT(), nullable=True)
    steps = db.relationship("ManualJobStep", backref="manual_job", cascade="all, delete")
    analyzeds = db.relationship('Analyzed', backref='manual_job')

    def to_json(self):
        executor_name = User.query.filter_by(user_id=self.creator_id).first().user_name  # 这里没有用backref
        milestone_name = Milestone.query.filter_by(id=self.milestone_id).first().name
        _case = Case.query.filter_by(id=self.case_id).first()
        steps = ManualJobStep.query.filter_by(manual_job_id=self.id).all()
        return {
            "id": self.id,
            "name": self.name,
            "case_id": self.case_id,
            "create_time": self.create_time,
            "update_time": self.update_time, 
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_step": self.total_step,
            "current_step": self.current_step,
            "executor_name": executor_name,
            "milestone_name": milestone_name,
            "result": self.result,
            "status": self.status,
            "case_name": _case.name,
            "case_description": _case.description,
            "case_preset": _case.preset,
            "case_expection": _case.expection,
            "creator_id": self.creator_id,
            "remark": self.remark,
            "steps": [s.to_json() for s in steps]
        }


class ManualJobStep(BaseModel, db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    log_content = db.Column(LONGTEXT, nullable=True)
    passed = db.Column(db.Boolean(), nullable=True)
    step_num = db.Column(db.Integer(), nullable=False)
    operation = db.Column(db.Text(), nullable=True)  # 操作内容, 是这个manual_job_step所属的manual_job所属的case的steps字段经文本分割的结果

    manual_job_id = db.Column(db.Integer(), db.ForeignKey("manual_job.id"))

    def to_json(self):
        return {
            "id": self.id,
            "log_content": self.log_content,
            "passed": self.passed,
            "step_num": self.step_num,
            "operation": self.operation,
        }