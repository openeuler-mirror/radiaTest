from flask_restful import Api
from .routes import Msg, MsgBatch


def init_api(api: Api):
    api.add_resource(Msg, '/api/v1/msg', endpoint='msg')
    api.add_resource(MsgBatch, '/api/v1/msg/batch', endpoint='msg_batch')
