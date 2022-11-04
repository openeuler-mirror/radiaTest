from flask_restful import Api
from server.apps.message.routes import Msg, MsgBatch, MsgCallBack, AddGroupMsgCallBack, MsgGetGroup


def init_api(api: Api):
    api.add_resource(Msg, '/api/v1/msg', endpoint='msg')
    api.add_resource(MsgBatch, '/api/v1/msg/batch', endpoint='msg_batch')
    api.add_resource(MsgGetGroup, '/api/v1/msg/group', endpoint='msg_group')
    api.add_resource(MsgCallBack, '/api/v1/msg/callback', endpoint='msg_callback')
    api.add_resource(AddGroupMsgCallBack, '/api/v1/msg/addgroup/callback', endpoint='msg_addgroup_callback')
