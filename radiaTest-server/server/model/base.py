import json
import datetime
import re

from server import db, socketio


class BaseModel(object):
    create_time = db.Column(db.DateTime(), default=datetime.datetime.now)
    update_time = db.Column(
        db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    def convert_time_format(self, t):
        if isinstance(t, datetime.date):
            return t.strftime("%Y-%m-%d")
        else:
            return t

    def add_update(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.commit()
        self._emit(table, namespace, broadcast)

    def delete(self, table=None, namespace=None, broadcast=False):
        db.session.delete(self)
        db.session.commit()
        self._emit(table, namespace, broadcast)

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.flush()
        record_id = None
        if hasattr(self, "id"):  # id写死在代码里, 实际上有可能叫uid或uuid.
            record_id = self.id
        db.session.commit()

        self._emit(table, namespace, broadcast)

        return record_id

    def add_flush_commit(self, table=None, namespace=None, broadcast=False):
        db.session.add(self)
        db.session.flush()
        record = self
        db.session.commit()

        self._emit(table, namespace, broadcast)

        return record

    def _emit(self, table, namespace, broadcast):
        if table and namespace:
            socketio.emit(
                "update",
                namespace=namespace,
                broadcast=broadcast,
            )


class PermissionBaseModel(object):
    permission_type = db.Column(
        db.Enum(
            "person",  # 个人
            "group",  # 团队
            "org",  # 组织
            "public"  # 公共
        ),
        default="person"
    )


class EmitDataModel(BaseModel):
    def _emit(self, table, namespace, broadcast):
        if table and namespace:
            socketio.emit(
                "update",
                json.dumps([item.to_json() for item in table.query.all()]),
                namespace=namespace,
                broadcast=broadcast,
            )


class ServiceModel(BaseModel):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(256))
    ip = db.Column(db.String(15), nullable=True)
    listen = db.Column(db.Integer())


class CasbinRoleModel(BaseModel):
    dom_pattern = r'^/api/v[0-9]+/([^/]+).*$'

    def _get_subject(self, role_type, role_name):
        """get subject by relationship between group/organization and role"""
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
                self.role.group.id
            )
        else:
            return "{}@org_{}".format(
                role_name,
                self.role.organization.id
            )

    def _get_subject_(self, role_type, role_name):
        """get subject by self group/organization"""
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
                self.group.id
            )
        else:
            return "{}@org_{}".format(
                role_name,
                self.organization.id,
            )

    def _get_dom(self, uri: str):
        """get domain of resource uri"""
        _result = re.match(CasbinRoleModel.dom_pattern, uri)
        if not _result:
            return None

        return _result.group(1)
        