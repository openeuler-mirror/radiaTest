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
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    data = db.Column(db.Text(), nullable=False)
    level = db.Column(db.Integer(), nullable=False, default=MsgLevel.user.value)
    from_id = db.Column(db.Integer(), nullable=False)
    to_id = db.Column(db.Integer(), nullable=False)
    is_delete = db.Column(db.Boolean(), default=False, nullable=False)
    has_read = db.Column(db.Boolean(), default=False, nullable=False)
    type = db.Column(db.Integer(), nullable=False, default=MsgType.text.value)

    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data,
            "level": self.level,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "is_delete": self.is_delete,
            "has_read": self.has_read,
            "type": self.type,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def add_update(self, table=None, namespace=None, broadcast=False):
        if not self.id:
            self.emit_notify()
        super().add_update(table, namespace, broadcast)
        self.emit_count()

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        id = super().add_flush_commit_id(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return id

    def add_flush_commit(self, table=None, namespace=None, broadcast=False):
        message = super().add_flush_commit(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return message

    def emit_count(self):
        from flask_socketio import emit
        emit(
            "count",
            {
                "num": Message.query.filter(
                    Message.to_id == self.to_id,
                    Message.is_delete == False,
                    Message.has_read == False).count()
            },
            namespace='/message',
            room=str(self.to_id)
        )

    def emit_notify(self):
        from flask_socketio import emit
        emit(
            "notify",
            {
                "content": json.loads(self.data).get('info')
            },
            namespace='/message',
            room=str(self.to_id)
        )

    @staticmethod
    def create_instance(data, from_id, to_id, level=MsgLevel.user.value, msg_type=MsgType.text.value):
        new_recode = Message()
        new_recode.data = json.dumps(data)
        new_recode.from_id = from_id
        new_recode.to_id = to_id
        new_recode.level = level
        new_recode.type = msg_type
        return new_recode
