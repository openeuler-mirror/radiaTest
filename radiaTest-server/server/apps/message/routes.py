from flask import g
from flask_socketio import join_room, leave_room, rooms, emit
from flask_restful import Resource
from flask_pydantic import validate

from server import socketio, redis_client
from server.model.message import Message
from server.schema.message import MessageCallBack
from server.utils.auth_util import auth, verify_token
from server.utils.response_util import response_collect
from server.apps.message.handlers import (
    handler_msg_list,
    handler_update_msg,
    handler_msg_callback,
    handler_addgroup_msg_callback,
    handler_group_page
)
from server.utils.redis_util import RedisKey


@socketio.on('after connect', namespace="/message")
def after_connect(token):
    """
    与客户端建立连接后执行
    """
    flag, user_id = False, None
    _verify_result = verify_token(token)
    if isinstance(_verify_result, tuple):
        flag, user_id = _verify_result

    # 若检验出user_id，将此客户端添加到user_id的room中
    if flag is True and user_id is not None:
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        join_room(str(user_id))
        msg_count = Message.query.filter(
            Message.to_id == g.user_id,
            Message.is_delete.is_(False),
            Message.has_read.is_(False),
            Message.org_id == org_id
        ).count()
        emit(
            "count",
            {"num": msg_count},
            namespace='/message',
            room=str(g.user_id)
        )


@socketio.on('disconnect', namespace="/message")
def on_disconnect():
    """
    与客户端断开连接时执行,将客户端从所有房间中移除
    """
    this_rooms = rooms()
    for room in this_rooms:
        leave_room(room)


class Msg(Resource):

    @auth.login_required()
    @response_collect
    def get(self):
        return handler_msg_list()


class MsgBatch(Resource):
    @auth.login_required()
    @response_collect
    def put(self):
        return handler_update_msg()


class MsgCallBack(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: MessageCallBack):
        return handler_msg_callback(body)


class AddGroupMsgCallBack(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def put(self, body: MessageCallBack):
        return handler_addgroup_msg_callback(body)


class MsgGetGroup(Resource):
    @auth.login_required()
    @response_collect
    def get(self):
        """
        消息中心获取当前用户所属的用户组
        :return:
        """
        return handler_group_page()
