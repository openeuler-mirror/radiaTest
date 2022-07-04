from flask_socketio import join_room, leave_room, rooms
from flask_restful import Resource
from flask_pydantic import validate

from server import socketio
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *
from server.schema.message import MessageCallBack
from server.utils.auth_util import verify_token


@socketio.on('after connect', namespace="/message")
def after_connect(token):
    """
    与客户端建立连接后执行
    """
    flag, gitee_id = False, None
    _verify_result = verify_token(token)
    if isinstance(_verify_result, tuple):
        flag, gitee_id = _verify_result
        
    # 若检验出user_id，将此客户端添加到user_id的room中
    if flag is True and gitee_id is not None:
        join_room(str(gitee_id))
        msg_count = Message.query.filter(
            Message.to_id == g.gitee_id,
            Message.is_delete == False,
            Message.has_read == False
        ).count()
        emit(
            "count",
            {"num": msg_count},
            namespace='/message',
            room=str(g.gitee_id)
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
