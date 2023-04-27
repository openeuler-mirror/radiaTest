from server import db
from server.model import BaseModel, PermissionBaseModel


class Framework(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "framework"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    logs_path = db.Column(db.String(256))
    adaptive = db.Column(db.Boolean(), nullable=False, default=False)
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))
    gitee_repos = db.relationship('GitRepo', backref='framework')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "logs_path": self.logs_path,
            "adaptive": self.adaptive,
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class GitRepo(db.Model, PermissionBaseModel, BaseModel):
    __tablename__ = "git_repo"

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    git_url = db.Column(db.String(256), nullable=False)
    branch = db.Column(db.String(64), nullable=False, default="master")
    sync_rule = db.Column(db.Boolean(), nullable=False, default=True)
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))
    group_id = db.Column(db.Integer(), db.ForeignKey("group.id"))
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    framework_id = db.Column(db.Integer(), db.ForeignKey("framework.id"))

    suites = db.relationship('Suite', backref='git_repo')

    templates = db.relationship('Template', backref='git_repo')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "git_url": self.git_url,
            "branch": self.branch,
            "sync_rule": self.sync_rule,
            "framework": self.framework.to_json(),
            "creator_id": self.creator_id,
            "permission_type": self.permission_type,
            "group_id": self.group_id,
            "org_id": self.org_id,
        }
