from server import db
from server.model import BaseModel


class Framework(db.Model, BaseModel):
    __tablename__ = "framework"
    name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    logs_path = db.Column(db.String(256))
    adaptive = db.Column(db.Boolean(), nullable=False, default=False)

    gitee_repos = db.relationship('GitRepo', backref='framework')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "logs_path": self.logs_path,
            "adaptive": self.adaptive,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }


class GitRepo(db.Model, BaseModel):
    __tablename__ = "git_repo"
    name = db.Column(db.String(64), nullable=False)
    git_url = db.Column(db.String(256), unique=True, nullable=False)
    sync_rule = db.Column(db.Boolean(), nullable=False, default=True)

    framework_id = db.Column(db.Integer(), db.ForeignKey("framework.id"))

    suites = db.relationship('Suite', backref='git_repo')

    templates = db.relationship('Template', backref='git_repo')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "git_url": self.git_url,
            "sync_rule": self.sync_rule,
            "framework": self.framework.to_json(),
        }
