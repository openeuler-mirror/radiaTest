from flask_restful import Resource
from server import socketio
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *
from server.schema.message import MessageCallBack
from flask_pydantic import validate
from server.utils.auth_util import verify_token


@socketio.on('after_connect')
def on_connect(sid, token):
    """
    与客户端建立连接后执行
    """
    flag, gitee_id = verify_token(token)
    # 若检验出user_id，将此客户端添加到user_id的room中
    if flag and gitee_id:
        socketio.enter_room(sid, str(gitee_id))
        msg_count = Message.query.filter(Message.to_id == g.gitee_id,
                                         Message.is_delete == False,
                                         Message.has_read == False).count()
        emit(
            "count",
            {"num": msg_count},
            namespace='message',
            room=str(g.gitee_id)
        )


@socketio.on('before_disconnect')
def on_disconnect(sid):
    """
    与客户端断开连接时执行,将客户端从所有房间中移除
    """
    rooms = socketio.rooms(sid)
    for room in rooms:
        socketio.leave_room(sid, room)


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
