import json

from server.model.base import Base
from server import db
from enum import Enum


class MsgLevel(Enum):
    group = 2
    user = 1
    system = 0


class MsgType(Enum):
    text = 0
    script = 1


class Message(db.Model, Base):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    data = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False, default=MsgLevel.user.value)
    from_id = db.Column(db.Integer, nullable=False)
    to_id = db.Column(db.Integer, nullable=False)
    is_delete = db.Column(db.Boolean, default=False, nullable=False)
    has_read = db.Column(db.Boolean, default=False, nullable=False)
    type = db.Column(db.Integer, nullable=False, default=MsgType.text.value)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def create_instance(data, from_id, to_id, level=MsgLevel.user.value, msg_type=MsgType.text.value):
        new_recode = Message()
        new_recode.data = json.dumps(data)
        new_recode.from_id = from_id
        new_recode.to_id = to_id
        new_recode.level = level
        new_recode.type = msg_type
        return new_recode
