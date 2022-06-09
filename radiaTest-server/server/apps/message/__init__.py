from flask_restful import Api
from .routes import Msg, MsgBatch, MsgCallBack


def init_api(api: Api):
    api.add_resource(Msg, '/api/v1/msg', endpoint='msg')
    api.add_resource(MsgBatch, '/api/v1/msg/batch', endpoint='msg_batch')
    api.add_resource(MsgCallBack, '/api/v1/msg/callback', endpoint='msg_callback')
