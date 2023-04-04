import pandas as pd

from server import db
from server.model.base import BaseModel, PermissionBaseModel
from .group import Group
from .job import Analyzed
from .testcase import Suite
from .user import User

re_task_tag = db.Table('re_task_tag',
                       db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
                       db.Column('task_tag_id', db.Integer, db.ForeignKey('task_tag.id'), primary_key=True)
                       )

task_family = db.Table('task_family',
                       db.Column('parent_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
                       db.Column('child_id', db.Integer, db.ForeignKey('task.id'), primary_key=True)
                       )

task_case = db.Table('task_case',
                     db.Column('task_milestone_id', db.Integer, db.ForeignKey('task_milestone.id', ondelete="CASCADE"),
                               primary_key=True),
                     db.Column('case_id', db.Integer, db.ForeignKey('case.id', ondelete="CASCADE"), primary_key=True)
                     )


class TaskManualCase(db.Model, BaseModel):
    __tablename__ = 'task_manual_case'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_milestone_id = db.Column(db.Integer, db.ForeignKey('task_milestone.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    case_result = db.Column(db.Enum('success', 'failed', 'running'), default='running', nullable=False)

    def to_json(self):
        return {
            'id': self.id,
            'task_milestone_id': self.task_milestone_id,
            'case_id': self.case_id,
            'case_result': self.case_result,
        }


class TaskMilestone(db.Model, BaseModel):
    __tablename__ = "task_milestone"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestone.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=True)
    job_result = db.Column(db.Enum("block", "done", "running", "pending"), default="pending", nullable=False)

    cases = db.relationship('Case', secondary=task_case, backref=db.backref('task_milestone'),
                            cascade='all, delete',
                            passive_deletes=True)
    manual_cases = db.relationship('TaskManualCase', backref='task_milestone')

    def distribute_df_data(self, distribute_all_cases=True):
        df_list = []
        manual_df = pd.DataFrame([item.to_json() for item in self.manual_cases])
        for case in self.cases:
            if case.deleted:
                continue
            if case.usabled:
                analyzed = Analyzed.query.filter_by(job_id=self.job_id, case_id=case.id).first()
                case_result = analyzed.result if analyzed and analyzed.result else 'running'
            else:
                case_result = 'running'
                if not manual_df.empty:
                    case_result_se = manual_df[manual_df.case_id == case.id].case_result
                    if not case_result_se.empty:
                        case_result = case_result_se.to_list()[0]
            if distribute_all_cases:
                df_list.append((self.milestone_id, case.id, case.suite_id, case_result))
            else:
                if case_result.lower() != 'success':
                    df_list.append((self.milestone_id, case.id, case.suite_id, case_result))
        return df_list

    def to_json(self):
        auto_cases, manual_cases = [], []
        manual_df = pd.DataFrame([item.to_json() for item in self.manual_cases])
        for case in self.cases:
            if case.deleted:
                continue
            case_json = case.to_json()
            if case.usabled:
                case_result = self.job_result
                if self.job_result == 'block':
                    case_result = 'failed'
                elif self.job_result == 'done':
                    case_result = 'success'
                analyzed = Analyzed.query.filter_by(job_id=self.job_id, case_id=case.id).first()
                if analyzed:
                    case_result = analyzed.result if analyzed.result else case_result
                case_json['result'] = case_result
                auto_cases.append(case_json)
            else:
                case_result = 'running'
                if not manual_df.empty:
                    case_result_se = manual_df[manual_df.case_id == case.id].case_result
                    if not case_result_se.empty:
                        case_result = case_result_se.to_list()[0]
                case_json['result'] = case_result
                manual_cases.append(case_json)
        # return auto_cases, manual_cases
        return {
            'id': self.id,
            'task_id': self.task_id,
            'milestone_id': self.milestone_id,
            'job_id': self.job_id,
            'job_result': self.job_result,
            'auto_cases': auto_cases,
            'manual_cases': manual_cases
        }


class TaskParticipant(BaseModel, db.Model):
    """任务参与者表"""
    __tablename__ = "task_participant"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    participant_id = db.Column(db.Integer, nullable=False)  # 参与者id，可以是团队id或人员id
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)  # 归属任务id
    type = db.Column(  # 参与者类型
        db.Enum(
            "GROUP",  # 团队
            "PERSON"  # 个人
        ),
        default="PERSON")


class Task(db.Model, PermissionBaseModel, BaseModel):
    """任务表"""
    __tablename__ = "task"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))  # 任务发起人id
    type = db.Column(db.Enum("ORGANIZATION", "GROUP", "PERSON", "VERSION"), default="PERSON")
    start_time = db.Column(db.DateTime(), nullable=True)
    content = db.Column(db.Text, nullable=True)
    executor_id = db.Column(db.Integer, nullable=False)
    executor_type = db.Column(db.Enum("GROUP", "PERSON"), default="PERSON")
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=1)
    deadline = db.Column(db.DateTime(), nullable=True)
    accomplish_time = db.Column(db.DateTime(), nullable=True)
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    abstract = db.Column(db.Text, nullable=True)
    abbreviation = db.Column(db.Text, nullable=True)
    frame = db.Column(db.String(16), nullable=True)
    display = db.Column(db.Boolean, default=True, nullable=False)
    automatic = db.Column(db.Boolean, default=False, nullable=False)  # 是否是只有自动化用例的任务
    automatic_finish = db.Column(db.Boolean, default=False, nullable=False)  # 子任务完成，任务是否自动完成
    is_manage_task = db.Column(db.Boolean, default=False, nullable=False)  # 是否管理型任务
    test_strategy = db.Column(db.Boolean, default=False, nullable=False)  # 测试策略任务
    status_id = db.Column(db.Integer, db.ForeignKey("task_status.id"), nullable=True)  # 任务分类表关联
    case_node_id = db.Column(db.Integer, db.ForeignKey("case_node.id"), nullable=True)

    comments = db.relationship("TaskComment", backref="task")  # 评论表关联
    participants = db.relationship("TaskParticipant", backref="task")
    tags = db.relationship('TaskTag', secondary=re_task_tag, backref='tasks')
    children = db.relationship("Task", secondary=task_family, primaryjoin=(task_family.c.parent_id == id),
                               secondaryjoin=(task_family.c.child_id == id),
                               backref=db.backref('parents', lazy='dynamic'),
                               lazy='dynamic')
    report = db.relationship("TaskReportContent", backref="task", uselist=False)

    milestones = db.relationship('TaskMilestone', backref='task')  # 关联的里程碑

    feature = db.relationship('FeatureList', backref='task') # 关联的特性

    requirement = db.relationship('Requirement', backref='task') # 关联的需求
    requirement_package = db.relationship('RequirementPackage', backref='task') # 关联的子需求

    def compare_type(self, child_type):
        if child_type == "PERSON":
            return True
        elif self.type == "ORGANIZATION" and child_type == "GROUP":
            return True
        else:
            return False


class TaskComment(BaseModel, PermissionBaseModel, db.Model):
    """评论"""

    __tablename__ = "task_comment"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=True)  # 内容
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)  # 归属任务id


class TaskStatus(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = "task_status"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    order = db.Column(db.Integer, nullable=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    tasks = db.relationship("Task", backref="task_status")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'order': self.order
        }


class TaskTag(BaseModel, db.Model):
    __tablename__ = "task_tag"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    color = db.Column(db.Integer, nullable=False)


class TaskReportContent(BaseModel, db.Model):
    __tablename__ = "task_report_content"
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), primary_key=True)
    # model_id = db.Column(db.Integer, db.ForeignKey("task_report_model.id"), primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))


class TaskDistributeTemplate(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = 'task_distribute_template'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    creator_id = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, nullable=False)
    types = db.relationship("DistributeTemplateType", backref="template")
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))

    def to_json(self):
        group = Group.query.filter_by(id=self.group_id, is_delete=False).first()
        return {
            'id': self.id,
            'name': self.name,
            'creator': User.query.get(self.creator_id).to_dict(),
            'group': group.to_dict() if group else None,
            'types': [item.to_json() for item in self.types],
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S")
        }


class DistributeTemplateType(BaseModel, PermissionBaseModel, db.Model):
    __tablename__ = 'distribute_template_type'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), nullable=False)
    creator_id = db.Column(db.String(512), db.ForeignKey("user.user_id"), nullable=False)
    executor_id = db.Column(db.String(512), db.ForeignKey("user.user_id"), nullable=False)
    suites = db.Column(db.Text, nullable=True)
    helpers = db.Column(db.Text, nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    template_id = db.Column(db.Integer, db.ForeignKey("task_distribute_template.id"))

    def to_json(self):
        suites = None
        if self.suites:
            _suites = self.suites.split(',')
            suites = [item.to_json() for item in Suite.query.filter(Suite.id.in_(_suites))]
        helpers = None
        if self.helpers:
            _helpers = self.helpers.split(',')
            helpers = [item.to_dict() for item in User.query.filter(User.user_id.in_(_helpers))]
        return {
            'id': self.id,
            'name': self.name,
            'creator': User.query.get(self.creator_id).to_dict(),
            'executor': User.query.get(self.executor_id).to_dict(),
            'suites': suites,
            'helpers': helpers,
            'create_time': self.create_time.strftime("%Y-%m-%d %H:%M:%S")
            # 'template': self.template.to_json()
        }
