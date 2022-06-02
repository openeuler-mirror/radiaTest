import json
import datetime

from server import db, socketio


class Base(object):
    create_time = db.Column(db.DateTime(), default=datetime.datetime.now)
    update_time = db.Column(
        db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    def add_update(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.commit()
        if table and namespace:
            socketio.emit(
                "update",
                namespace=namespace,
                broadcast=broadcast,
            )

    def delete(self, table=None, namespace=None, broadcast=False):
        db.session.delete(self)
        db.session.commit()
        if table and namespace:
            socketio.emit(
                "update",
                namespace=namespace,
                broadcast=broadcast,
            )

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.flush()
        record_id = None
        if hasattr(self, "id"):
            record_id = self.id
        db.session.commit()

        if table and namespace:
            socketio.emit(
                "update",
                namespace=namespace,
                broadcast=broadcast,
            )
        
        return record_id

    def add_flush_commit(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.flush()
        record = self
        db.session.commit()

        if table and namespace:
            socketio.emit(
                "update",
                namespace=namespace,
                broadcast=broadcast,
            )

        return record


class BaseModel(Base):
    id = db.Column(db.Integer(), primary_key=True)


class ServiceBaseModel(BaseModel):
    name = db.Column(db.String(64))
    description = db.Column(db.String(256))
    ip = db.Column(db.String(15), nullable=False)
    listen = db.Column(db.Integer())


class PermissionBaseModel(Base):
    permission_type = db.Column(db.Enum(
            "person",  # 个人
            "group",  # 团队
            "org",   # 组织
            "public" #公共
        ),default="person")


class CasbinRoleModel(BaseModel):
    def _get_subject(self, role_type, role_name):
        if role_type == "public":
            return "{}@public".format(
                role_name,
            )
        elif role_type == "person":
            return "{}".format(
                role_name,
            )
        elif role_type == "group":
            return "{}@group_{}".format(
                role_name,
                self.role.group.name
            )
        else:
            return "{}@org_{}".format(
                role_name,
                self.role.organization.name
            )

    def _get_subject_(self, role_type, role_name):
        if role_type == "public":
            return "{}@public".format(
                role_name,
            )
        elif role_type == "person":
            return "{}".format(
                role_name,
            )
        elif role_type == "group":
            return "{}@group_{}".format(
                role_name,
                self.group.name
            )
        else:
            return "{}@org_{}".format(
                role_name,
                self.organization.name,
            )