from enum import Enum

from server import db
from server.model import BaseModel, PermissionBaseModel
from server.model.permission import Role, ReUserRole


class OrganizationRole(Enum):
    admin = 2
    user = 0


class Organization(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "organization"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)

    enterprise_id = db.Column(db.String(50))
    enterprise_join_url = db.Column(db.String(512))
    oauth_client_id = db.Column(db.String(512))
    oauth_client_secret = db.Column(db.String(512))
    oauth_scope = db.Column(db.String(256))

    cla_verify_url = db.Column(db.String(512), nullable=True)
    cla_verify_params = db.Column(db.String(512), nullable=True)
    cla_verify_body = db.Column(db.String(512), nullable=True)
    cla_sign_url = db.Column(db.String(512), nullable=True)
    cla_request_type = db.Column(db.String(8), nullable=True)
    cla_pass_flag = db.Column(db.String(512), nullable=True)

    re_user_org = db.relationship("ReUserOrganization", cascade="all, delete", backref="organization")

    roles = db.relationship("Role", cascade="all, delete", backref="organization")

    re_org_publisher = db.relationship("RequirementPublisher", backref="org")

    def add_update(self, table=None, namespace=None, broadcast=False):
        from sqlalchemy.exc import IntegrityError
        from flask import current_app
        if self.is_delete:
            try:
                super().delete(table, namespace, broadcast)
                return True
            except IntegrityError as e:
                current_app.logger.error(f'database operate error -> {e}')
                return False
        else:
            super().add_update(table, namespace, broadcast)
            return True

    def to_dict(self):
        _dict = self.__dict__
        _dict.update({
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        _dict.pop('_sa_instance_state')

        return _dict

    def to_summary(self):
        return {
            "name": self.name,
            "description": self.description,
            "avatar_url": self.avatar_url,
        }

    @staticmethod
    def create(model):
        new_recode = Organization()
        new_recode.name = model.name
        new_recode.avatar_url = model.avatar_url
        new_recode.cla_sign_url = model.cla_sign_url
        new_recode.cla_verify_url = model.cla_verify_url
        new_recode.cla_verify_body = model.cla_verify_body
        new_recode.cla_pass_flag = model.cla_pass_flag
        new_recode.cla_verify_params = model.cla_verify_params
        new_recode.cla_request_type = model.cla_request_type
        new_recode.description = model.description
        new_recode.enterprise_id = model.enterprise_id
        new_recode.enterprise_join_url = model.enterprise_join_url
        new_recode.oauth_client_id = model.oauth_client_id
        new_recode.oauth_client_secret = model.oauth_client_secret
        new_recode.oauth_scope = model.oauth_scope
        new_id = new_recode.add_flush_commit_id()
        if not new_id:
            return None
        new_recode.id = new_id
        return new_recode


class ReUserOrganization(db.Model, BaseModel):
    __tablename__ = "re_user_organization"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    # 0 普通用户
    role_type = db.Column(db.Integer(), default=0, nullable=False)
    cla_info = db.Column(db.String(1024), nullable=True)
    default = db.Column(db.Boolean, default=False, nullable=False)
    rank = db.Column(db.Integer())

    user_gitee_id = db.Column(db.Integer, db.ForeignKey('user.gitee_id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    def to_dict(self):
        _dict = self.__dict__
        _filter = [ReUserRole.user_id == self.user_gitee_id, Role.type == 'org', Role.org_id == self.organization_id]
        _role = Role.query.join(ReUserRole).filter(*_filter).first()

        _dict.update({
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            "role": _role.to_json() if _role else None
        })

        return _dict

    @staticmethod
    def create(user_gitee_id, organization_id, cla_info, role_type=0, default=False):
        new_record = ReUserOrganization()
        new_record.user_gitee_id = user_gitee_id
        new_record.organization_id = organization_id
        new_record.role_type = role_type
        new_record.cla_info = cla_info
        new_record.default = default
        new_record.add_update()
        return new_record
