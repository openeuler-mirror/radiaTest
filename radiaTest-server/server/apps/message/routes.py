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

from flask import g
from flask_socketio import join_room, leave_room, rooms, emit
from flask_restful import Resource
from flask_pydantic import validate

from server import socketio, redis_client, swagger_adapt
from server.model.message import Message, MessageUsers
from server.schema.message import MessageCallBack, TextMessageModel
from server.utils.auth_util import auth, verify_token
from server.utils.response_util import response_collect
from server.apps.message.handlers import (
    handler_msg_list,
    handler_update_msg,
    handler_msg_callback,
    handler_addgroup_msg_callback,
    handler_group_page, handler_create_text_msg
)
from server.utils.redis_util import RedisKey


def get_message_tag():
    return {
        "name": "用户消息",
        "description": "用户消息相关接口",
    }


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
        msg_count = Message.query.join(MessageUsers).filter(
            MessageUsers.user_id == g.user_id,
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
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "Msg",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "获取用户消息列表",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求参数
        "query_schema_model": [{
            "name": "has_read",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "消息是否已读",
            "schema": {"type": "integer"}},
            {
            "name": "page_size",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "页大小",
            "schema": {"type": "integer"}},
            {
            "name": "page_num",
            "in": "query",
            "required": False,
            "style": "form",
            "explode": True,
            "description": "页码",
            "schema": {"type": "integer"}}],
    })
    def get(self):
        return handler_msg_list()


class MsgBatch(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MsgBatch",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "消息批量处理",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求体示例
        "request_schema_model": {
            "description": "",
            "content": {
                "application/json":
                    {"schema": {
                        "properties": {
                            "msg_ids": {
                                "title": "消息id列表",
                                'type': "array",
                                'items': {"type": "integer"}},
                            "is_delete": {
                                "title": "是否逻辑删除",
                                "type": "integer",
                                "enum": [0, 1]
                            },
                            "has_read": {
                                "title": "已读",
                                "type": "integer",
                                "enum": [0, 1]
                            },
                            "has_all_read": {
                                "title": "全部已读",
                                "type": "integer",
                                "enum": [0, 1]
                            }
                        },
                        "required": ["msg_id", "access"],
                        "title": "JoinGroupSchema",
                        "type": "object"
                    }}
            },
            "required": True
        }
    })
    def put(self):
        return handler_update_msg()


class MsgCallBack(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MsgCallBack",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "消息处理回调接口",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求体示例
        "request_schema_model": MessageCallBack
    })
    def put(self, body: MessageCallBack):
        return handler_msg_callback(body)


class AddGroupMsgCallBack(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "AddGroupMsgCallBack",  # 当前接口视图函数名
        "func_name": "put",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "加入用户组消息处理回调接口",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求体示例
        "request_schema_model": MessageCallBack
    })
    def put(self, body: MessageCallBack):
        return handler_addgroup_msg_callback(body)


class MsgGetGroup(Resource):
    @auth.login_required()
    @response_collect
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "MsgGetGroup",  # 当前接口视图函数名
        "func_name": "get",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "消息中心获取当前用户所属的用户组",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求参数
        "query_schema_model": [{
            "name": "name",
            "in": "query",
            "required": True,
            "style": "form",
            "explode": True,
            "description": "用户组名关键字",
            "schema": {"type": "string"}},
            {
                "name": "page_size",
                "in": "query",
                "required": True,
                "style": "form",
                "explode": True,
                "description": "页大小",
                "schema": {"type": "integer"}},
            {
                "name": "page_num",
                "in": "query",
                "required": True,
                "style": "form",
                "explode": True,
                "description": "页码",
                "schema": {"type": "integer"}}],
    })
    def get(self):
        """
        消息中心获取当前用户所属的用户组
        :return:
        """
        return handler_group_page()


class TextMsg(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @swagger_adapt.api_schema_model_map({
        "__module__": get_message_tag.__module__,  # 获取当前接口所在模块
        "resource_name": "TextMsg",  # 当前接口视图函数名
        "func_name": "post",  # 当前接口所对应的函数名
        "tag": get_message_tag(),  # 当前接口所对应的标签
        "summary": "创建文本消息",  # 当前接口概述
        "externalDocs": {"description": "", "url": ""},  # 当前接口扩展文档定义
        # 自定义请求体示例
        "request_schema_model": TextMessageModel
    })
    def post(self, body: TextMessageModel):
        return handler_create_text_msg(body)
