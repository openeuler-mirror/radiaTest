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

from server import db
from server.model.base import BaseModel


class ManualJob(BaseModel, db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    start_time = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    end_time = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    result = db.Column(db.String(255), nullable=True)
    current_step = db.Column(db.Integer(), nullable=False, default=0)
    total_step = db.Column(db.Integer(), nullable=False)

    executor_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    milestone_id = db.Column(db.Integer(), db.ForeignKey("milestone.id"))
    case_id = db.Column(db.Integer(), db.ForeignKey("case.id"))

    status = db.Column(db.Integer, nullable=False, default=0)  # 0: In progress, 1: Completed.

    steps = db.relationship("ManualJobStep", backref="manual_job", cascade="all, delete")

    def to_json(self):
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
            "executor_id": self.executor_id,
            "milestone_id": self.milestone_id,
            "result": self.result,
            "status": self.status
        }


class ManualJobStep(BaseModel, db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    log_content = db.Column(db.String(255), nullable=True)
    passed = db.Column(db.Boolean(), nullable=True)
    step_num = db.Column(db.Integer(), nullable=False)

    manual_job_id = db.Column(db.Integer(), db.ForeignKey("manual_job.id"))
    