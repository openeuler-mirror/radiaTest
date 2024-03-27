# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

import json
from enum import Enum

from server.model import BaseModel
from server import db
from server.utils.db import Insert


class MsgLevel(Enum):
    group = 2
    user = 1
    system = 0


class MsgType(Enum):
    text = 0
    script = 1


# 消息中间表
class MessageUsers(db.Model, BaseModel):
    __tablename__ = "message_users"
    message_id = db.Column(db.Integer(), db.ForeignKey('message.id'), primary_key=True)
    # user外键较多迁移存在问题，故逻辑关联、手动维护
    user_id = db.Column(db.String(512), primary_key=True)
    message = db.relationship("Message", backref="msg_users", cascade="all, delete")

    def add_update(self, table=None, namespace=None, broadcast=False):
        super().add_update(table, namespace, broadcast)
        self.emit_notify()
        self.emit_count()

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        msg_id = super().add_flush_commit_id(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return msg_id

    def add_flush_commit(self, table=None, namespace=None, broadcast=False):
        message_user = super().add_flush_commit(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return message_user

    def emit_count(self):
        from flask_socketio import emit
        emit(
            "count",
            {
                "num": Message.query.join(MessageUsers).filter(
                    MessageUsers.user_id == self.user_id,
                    Message.is_delete.is_(False),
                    Message.has_read.is_(False)).count()
            },
            namespace='/message',
            room=str(self.user_id)
        )

    def emit_notify(self):
        from flask_socketio import emit
        data = json.loads(self.message.data)
        if data and data.get('info'):
            emit(
                "notify",
                {
                    "content": json.loads(self.message.data).get('info')
                },
                namespace='/message',
                room=str(self.user_id)
            )


class Message(db.Model, BaseModel):
    __tablename__ = "message"
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    data = db.Column(db.Text(), nullable=False)
    level = db.Column(db.Integer(), nullable=False, default=MsgLevel.user.value)
    from_id = db.Column(db.String(512), nullable=False)
    is_delete = db.Column(db.Boolean(), default=False, nullable=False)
    has_read = db.Column(db.Boolean(), default=False, nullable=False)
    type = db.Column(db.Integer(), nullable=False, default=MsgType.text.value)
    org_id = db.Column(db.Integer(), db.ForeignKey("organization.id"))

    @staticmethod
    def create_instance(data, from_id, to_ids, org_id, level=MsgLevel.user.value, msg_type=MsgType.text.value):
        new_recode = Message()
        if isinstance(data, str):
            new_recode.data = data
        else:
            new_recode.data = json.dumps(data)
        new_recode.from_id = from_id
        new_recode.level = level
        new_recode.type = msg_type
        new_recode.org_id = org_id
        message_id = new_recode.add_flush_commit_id()
        # 消息关联用户
        if isinstance(to_ids, (list, tuple, set)):
            for msg_user_id in to_ids:
                Insert(MessageUsers,
                       {
                           "user_id": msg_user_id,
                           "message_id": message_id,
                       }).single()
        else:
            Insert(MessageUsers,
                   {
                       "user_id": to_ids,
                       "message_id": message_id,
                   }).single()
        return new_recode

    def to_dict(self):
        return {
            "id": self.id,
            "data": self.data,
            "level": self.level,
            "from_id": self.from_id,
            "is_delete": self.is_delete,
            "has_read": self.has_read,
            "type": self.type,
            "org_id": self.org_id,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": self.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def add_update(self, table=None, namespace=None, broadcast=False):
        if not self.id:
            self.emit_notify()
        super().add_update(table, namespace, broadcast)
        self.emit_count()

    def add_flush_commit_id(self, table=None, namespace=None, broadcast=False):
        record_id = super().add_flush_commit_id(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return record_id

    def add_flush_commit(self, table=None, namespace=None, broadcast=False):
        message = super().add_flush_commit(table, namespace, broadcast)
        self.emit_count()
        self.emit_notify()
        return message

    def emit_count(self):
        from flask_socketio import emit
        for mes_user in self.msg_users:
            emit(
                "count",
                {
                    "num": Message.query.join(MessageUsers).filter(
                        MessageUsers.user_id == mes_user.user_id,
                        Message.is_delete.is_(False),
                        Message.has_read.is_(False),
                        Message.org_id == self.org_id).count()
                },
                namespace='/message',
                room=str(mes_user.user_id)
            )

    def emit_notify(self):
        from flask_socketio import emit
        for mes_user in self.msg_users:
            emit(
                "notify",
                {
                    "content": json.loads(self.data).get('info')
                },
                namespace='/message',
                room=str(mes_user.user_id)
            )
