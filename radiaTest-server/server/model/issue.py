# Copyright (c) [2023] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
# @Date    : 2023/03/15
# @License : Mulan PSL v2
#####################################

from server.model import BaseModel
from server import db


class Issue(db.Model, BaseModel):
    __tablename__ = "issue"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    title = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text(), nullable=True)
    priority = db.Column(db.Integer(), nullable=False, default=0)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    milestone_id = db.Column(db.Integer(), nullable=False)
    task_id = db.Column(db.Integer(), nullable=True)
    case_id = db.Column(db.Integer(), nullable=True)
    project_name = db.Column(db.String(128), nullable=False)
    issue_type_id = db.Column(db.Integer(), nullable=False)
    ident = db.Column(db.String(128), nullable=False)
    gitee_issue_id = db.Column(db.Integer(), nullable=False)
    gitee_issue_url = db.Column(db.String(128), nullable=False)

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'creator_id': self.creator_id,
            'milestone_id': self.milestone_id,
            'task_id': self.task_id,
            'case_id': self.case_id,
            'project_name': self.project_name,
            'issue_type_id': self.issue_type_id,
            "ident": self.ident,
            "gitee_issue_id": self.gitee_issue_id,
            "gitee_issue_url": self.gitee_issue_url,
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            'update_time': self.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }
