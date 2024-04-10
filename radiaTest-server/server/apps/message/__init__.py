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
# @Date    : 2023/09/04
# @License : Mulan PSL v2
#####################################

from flask_restful import Api
from server.apps.message.routes import Msg, MsgBatch, MsgCallBack, AddGroupMsgCallBack, MsgGetGroup, TextMsg


def init_api(api: Api):
    api.add_resource(Msg, '/api/v1/msg', endpoint='msg')
    api.add_resource(MsgBatch, '/api/v1/msg/batch', endpoint='msg_batch')
    api.add_resource(MsgGetGroup, '/api/v1/msg/group', endpoint='msg_group')
    api.add_resource(MsgCallBack, '/api/v1/msg/callback', endpoint='msg_callback')
    api.add_resource(AddGroupMsgCallBack, '/api/v1/msg/addgroup/callback', endpoint='msg_addgroup_callback')
    # 文本消息创建接口
    api.add_resource(TextMsg, '/api/v1/msg/text_msg', endpoint='text_msg')
