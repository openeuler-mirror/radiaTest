from server.model.base import Base
from server import db
from enum import Enum


class GroupRole(Enum):
    create_user = 1
    admin = 2
    user = 3
    no_reviewer = 0


class Group(db.Model, Base):
    __tablename__ = "group"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)

    re_user_group = db.relationship("ReUserGroup", backref="group")

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def create(name, description=None, avatar_url=None):
        new_recode = Group()
        new_recode.name = name
        new_recode.description = description
        new_recode.avatar_url = avatar_url
        group_id = new_recode.add_flush_commit()
        return group_id


class ReUserGroup(db.Model, Base):
    __tablename__ = "re_user_group"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_add_group_flag = db.Column(db.Boolean, default=False, nullable=False)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    # 0 待加入用户；1 创建者；2 管理员；3 普通用户
    role_type = db.Column(db.Integer, default=0, nullable=False)
    user_gitee_id = db.Column(db.Integer, db.ForeignKey('user.gitee_id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    org_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def create(flag, role_type, user_gitee_id, group_id, org_id):
        new_recode = ReUserGroup()
        new_recode.user_add_group_flag = flag
        new_recode.role_type = role_type
        new_recode.user_gitee_id = user_gitee_id
        new_recode.group_id = group_id
        new_recode.org_id = org_id
        new_recode.add_update()
