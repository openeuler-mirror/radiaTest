from server import db
from server.model import BaseModel


class CeleryTask(db.Model, BaseModel):
    __tablename__ = "celerytask"

    id = db.Column(db.Integer(), primary_key=True)
    tid = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(128), nullable=False, default="PENDING")
    start_time = db.Column(db.DateTime(), nullable=True)
    running_time = db.Column(db.Integer(), nullable=True)
    object_type = db.Column(db.String(64), nullable=False)
    vmachine_id = db.Column(db.Integer(), db.ForeignKey("vmachine.id"))
    pmachine_id = db.Column(db.Integer(), db.ForeignKey("pmachine.id"))
    description = db.Column(db.String(128))

    user_id = db.Column(db.String(512), db.ForeignKey("user.user_id"))

    def to_dict(self):
        _machine = None
        if self.object_type == "vmachine":
            _machine = self.vmachine.to_public_json()
        elif self.object_type == "pmachine":
            _machine = self.pmachine.to_public_json()

        _start_time = None
        if self.start_time:
            _start_time = self.start_time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "tid": self.tid,
            "status": self.status,
            "start_time": _start_time,
            "running_time": self.running_time,
            "object_type": self.object_type,
            "machine": _machine,
            "description": self.description,
            "user_id": self.user_id,
        }
    
    def to_json(self):
        return self.to_dict()
