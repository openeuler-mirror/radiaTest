import json
import datetime

from server import db, socketio
from server.utils import DateEncoder


class Base(object):
    create_time = db.Column(db.DateTime(), default=datetime.datetime.now)
    update_time = db.Column(
        db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    def add_update(self, table=None, namespace=None):
        db.session.add(self)
        db.session.commit()
        if table and namespace:
            socketio.emit(
                "update",
                json.dumps([item.to_json() for item in table.query.all()], cls=DateEncoder),
                namespace=namespace,
            )

    def delete(self, table, namespace):
        db.session.delete(self)
        db.session.commit()
        socketio.emit(
            "update",
            json.dumps([item.to_json() for item in table.query.all()], cls=DateEncoder),
            namespace=namespace,
        )

    def add_flush_commit(self, table=None, namespace=None):
        db.session.add(self)
        db.session.flush()
        record_id = None
        if hasattr(self, "id"):
            record_id = self.id
        db.session.commit()

        if table and namespace:
            socketio.emit(
                "update",
                json.dumps([item.to_json() for item in table.query.all()], cls=DateEncoder),
                namespace=namespace,
            )
        
        return record_id


class BaseModel(Base):
    id = db.Column(db.Integer(), primary_key=True)
