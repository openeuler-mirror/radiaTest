from server.model.base import Base
from server import db


class Organization(db.Model, Base):
    __tablename__ = "organization"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    enterprise = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    cla_verify_url = db.Column(db.String(512), nullable=False)
    cla_verify_params = db.Column(db.String(512), nullable=True)
    cla_verify_body = db.Column(db.String(512), nullable=True)
    cla_sign_url = db.Column(db.String(512), nullable=False)
    cla_request_type = db.Column(db.String(8), nullable=False)
    cla_pass_flag = db.Column(db.String(512), nullable=False)

    re_user_org = db.relationship("ReUserOrganization", backref="organization")

    def to_dict(self):
        return self.__dict__

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
        new_recode.enterprise = model.enterprise
        new_id = new_recode.add_flush_commit()
        if not new_id:
            return None
        new_recode.id = new_id
        return new_recode


class ReUserOrganization(db.Model, Base):
    __tablename__ = "re_user_organization"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    # 0 普通用户
    role_type = db.Column(db.Integer, default=0, nullable=False)
    cla_info = db.Column(db.String(1024), nullable=True)
    default = db.Column(db.Boolean, default=False, nullable=False)

    user_gitee_id = db.Column(db.Integer, db.ForeignKey('user.gitee_id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def create(user_gitee_id, organization_id, cla_info, role_type=0, default=False):
        new_record = ReUserOrganization()
        new_record.user_gitee_id = user_gitee_id
        new_record.organization_id = organization_id
        new_record.role_type = role_type
        new_record.cla_info = cla_info
        new_record.default = default
        return new_record
