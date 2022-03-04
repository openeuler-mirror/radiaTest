from email.policy import default
from server import db
from server.model import BaseModel


class CeleryTask(db.Model, BaseModel):
    __tablename__ = "celerytask"
    tid = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(128), nullable=False, default="PENDING")
    start_time = db.Column(db.String(128), nullable=True)
    running_time = db.Column(db.Integer(), nullable=True)
    object_type = db.Column(db.String(64), nullable=False)
    vmachine_id = db.Column(db.Integer(), db.ForeignKey("vmachine.id"))
    pmachine_id = db.Column(db.Integer(), db.ForeignKey("pmachine.id"))
    description = db.Column(db.String(128))

    user_id = db.Column(db.Integer(), db.ForeignKey("user.gitee_id"))

    def to_dict(self):
        _machine = None
        if self.object_type == "vmachine":
            _machine = self.vmachine.to_json()
        elif self.object_type == "pmachine":
            _machine = self.pmachine.to_json()

        return {
            "tid": self.tid,
            "status": self.status,
            "start_time": self.start_time,
            "running_time": self.running_time,
            "object_type": self.object_type,
            "machine": _machine,
            "description": self.description,
            "user_id": self.user_id,
        }
    
    def to_json(self):
        return self.to_dict()
