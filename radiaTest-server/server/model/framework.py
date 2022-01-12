from server import db
from server.model import BaseModel

class Framework(db.Model, BaseModel):
    __tablename__ = "framework"
    name = db.Column(db.String(64), unique=True, nullable=False)
    url = db.Column(db.String(256), unique=True, nullable=False)
    logs_path = db.Column(db.String(256))
    adaptive = db.Column(db.Boolean(), nullable=False)

    suites = db.relationship('Suite', backref='framework')

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "logs_path": self.logs_path,
            "adaptive": self.adaptive,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }