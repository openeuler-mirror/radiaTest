from flask_restful import Resource
from server import socketio
from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from .handlers import *
from server.schema.message import MessageCallBack
from flask_pydantic import validate


@socketio.on('count', namespace='/api/v1/msg')
def get_msg_count(gitee_id):
    return handler_user_msg_count(gitee_id)


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
