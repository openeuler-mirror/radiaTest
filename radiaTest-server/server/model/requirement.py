from datetime import timedelta
from sqlalchemy.dialects.mysql import LONGTEXT

from server import db
from server.model.base import BaseModel
from server.model.user import User
from server.model.milestone import Milestone


def _to_list(data):
    return data.split(',') if data else None


def _get_user_summary(user_id):
    _user = User.query.filter_by(gitee_id=user_id).first()
    if not _user:
        return None
    return _user.to_summary()


requirement_milestone = db.Table('requirement_milestone',
    db.Column(
        'requirement_id', 
        db.Integer(), 
        db.ForeignKey(
            'requirement.id', 
            ondelete="CASCADE"
        ),
        primary_key=True
    ),
    db.Column(
        'milestone_id', 
        db.Integer(), 
        db.ForeignKey(
            'milestone.id', 
        ), 
        primary_key=True
    )
)


class Requirement(db.Model, BaseModel):
    __tablename__ = "requirement"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    status = db.Column(db.String(64))
    title = db.Column(db.String(128))
    remark = db.Column(db.String(512))
    description = db.Column(LONGTEXT())
    payload = db.Column(db.Float())
    period = db.Column(db.Integer(), nullable=False, default=0)
    influence_require = db.Column(db.Integer(), nullable=False, default=0)
    behavior_require = db.Column(db.Integer(), nullable=False, default=0)
    total_reward = db.Column(db.Integer(), nullable=False, default=0)
    dividable_reward = db.Column(db.Integer(), nullable=False, default=0)    
    statement_filelist = db.Column(db.String(512))
    statement_locked = db.Column(db.Boolean(), default=False)
    progress_filelist = db.Column(db.String(512))
    progress_locked = db.Column(db.Boolean(), default=False)
    validation_filelist = db.Column(db.String(512))
    validation_locked = db.Column(db.Boolean(), default=False)

    task_id = db.Column(db.Integer(), db.ForeignKey("task.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    publisher = db.relationship("RequirementPublisher", backref="requirement", cascade="all, delete, delete-orphan")
    acceptor = db.relationship("RequirementAcceptor", backref="requirement", cascade="all, delete, delete-orphan")
    packages = db.relationship("RequirementPackage", backref="requirement", cascade="all, delete, delete-orphan")
    progresses = db.relationship("RequirementProgress", backref="requirement", cascade="all, delete, delete-orphan")
    milestones = db.relationship("Milestone", secondary=requirement_milestone)

    def to_json(self):    
        return {
            "id": self.id,
            "status": self.status,
            "title": self.title,
            "remark": self.remark,
            "description": self.description,
            "payload": self.payload,
            "period": self.period,
            "influence_require": self.influence_require,
            "behavior_require": self. behavior_require,
            "total_reward": self.total_reward,
            "dividable_reward": self.dividable_reward,
            "publisher": self.publisher[0].to_json() if self.publisher else None,
            "acceptor": self.acceptor[0].to_json() if self.acceptor else None,
            "task_id": self.task_id,
            "create_time": self.create_time.strftime("%Y-%m-%d"),
            "update_time": self.update_time.strftime("%Y-%m-%d-%H-%M-%S"),
            "filelist_locked": {
                "statement": self.statement_locked,
                "progress": self.progress_locked,
                "validation": self.validation_locked,
            },
            "milestones": list(map(lambda ms: ms.name, self.milestones)),
        }

    def get_filelist(self, _type):
        _filelist = None
        if _type == "statement":
            _filelist = _to_list(self.statement_filelist)
        elif _type == "progress":
            _filelist = _to_list(self.progress_filelist)
        elif _type == "validation":
            _filelist = _to_list(self.validation_filelist)
        
        return [] if not _filelist else _filelist


class RequirementPublisher(db.Model, BaseModel):
    __tablename__ = "requirement_publisher"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    type = db.Column(db.String(64))

    user_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    requirement_id = db.Column(db.Integer(), db.ForeignKey("requirement.id"))

    def to_json(self):
        if self.type == "group" and self.group_id:
            return_data = self.group.to_summary()
            return_data.update({
                "type": self.type,
                "group_id": self.group_id,
                "gitee_id": self.user_id,
            })
            return return_data
        elif self.type == "person" and self.user_id:
            return_data = self.user.to_summary()
            return_data.update({
                "type": self.type,
            })
            return return_data
        elif self.type == "organization" and self.org_id:
            return_data = self.org.to_summary()
            return_data.update({
                "type": self.type,
                "org_id": self.org_id,
                "gitee_id": self.user_id,
            })
            return return_data
        else:
            return {}


class RequirementAcceptor(db.Model, BaseModel):
    __tablename__ = "requirement_acceptor"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    type = db.Column(db.String(64))

    user_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    requirement_id = db.Column(db.Integer(), db.ForeignKey("requirement.id"))

    def to_json(self):
        if self.type == "group" and self.group_id:
            return_data = self.group.to_summary()
            return_data.update({
                "type": self.type,
                "gitee_id": self.user_id,
                "group_id": self.group_id,
                "start_time": self.create_time.strftime("%Y-%m-%d"),
                "estimated_finish_time": (
                    self.create_time + timedelta(days=self.requirement.period)
                ).strftime("%Y-%m-%d"),
            })
            return return_data
        elif self.type == "person" and self.user_id:
            return_data = self.user.to_summary()
            return_data.update({
                "type": self.type,
                "start_time": self.create_time.strftime("%Y-%m-%d"),
                "estimated_finish_time": (
                    self.create_time + timedelta(days=self.requirement.period)
                ).strftime("%Y-%m-%d"),
            })
            return return_data
        else:
            return {}


class RequirementPackage(db.Model, BaseModel):
    __tablename__ = "requirement_package"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    targets = db.Column(db.String(128))
    completions = db.Column(db.String(128))
    
    requirement_id = db.Column(db.Integer(), db.ForeignKey("requirement.id"))
    validator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    task_id = db.Column(db.Integer(), db.ForeignKey("task.id"))

    def to_json(self):
        _task_status = None
        _task_executor = None
        _task_participants = []

        if self.task_id:
            _task_status = self.task.task_status.name
            _task_executor = _get_user_summary(self.task.executor_id)
            for participant in self.task.participants:
                _participant_user = User.query.filter_by(gitee_id=participant.participant_id).first()
                if _participant_user:
                    _task_participants.append(_participant_user.to_summary())

        return {
            "id": self.id,
            "name": self.name,
            "targets": _to_list(self.targets),
            "completions": _to_list(self.completions),
            "requirement_id": self.requirement_id,
            "status": _task_status,
            "executor": _task_executor,
            "participants": _task_participants,
            "validator": self.validator.to_summary() if self.validator else None,
        }


class RequirementProgress(db.Model, BaseModel):
    __tablename__ = "requirement_progress"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    type = db.Column(db.String(32))
    percentage = db.Column(db.Integer(), default=0)
    content = db.Column(LONGTEXT(), nullable=False)

    requirement_id = db.Column(db.Integer(), db.ForeignKey("requirement.id"))

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type,
            "percentage": self.percentage,
            "content": self.content,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        }