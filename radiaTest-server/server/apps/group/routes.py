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

from server import casbin_enforcer
from flask_restful import Resource
from flask_pydantic import validate

from server.apps.group.handlers import (
    handler_add_group,
    handler_update_group,
    handler_delete_group,
    handler_group_page,
    handler_group_user_page,
    handler_add_user,
    handler_update_user,
    handler_apply_join_group
)
from server.schema.group import AddGroupUserSchema, UpdateGroupUserSchema, QueryGroupUserSchema
from server.utils.auth_util import auth
from server.utils.response_util import response_collect


class Group(Resource):
    @auth.login_required()
    @response_collect
    def post(self):
        """
        创建一个用户组
        :return:
        """
        return handler_add_group()

    @auth.login_required()
    @response_collect
    @casbin_enforcer.enforcer
    def put(self, group_id):
        """
        编辑用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_update_group(group_id)

    @auth.login_required()
    @response_collect
    def delete(self, group_id):
        """
        退出/删除用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_delete_group(group_id)

    @auth.login_required()
    @response_collect
    def get(self):
        """
        获取当前用户所属的用户组
        :return:
        """
        return handler_group_page()


class User(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def get(self, group_id, query: QueryGroupUserSchema):
        """
        获取某一用户组下的所有用户
        :param group_id: 用户组ID
        :return:
        """
        return handler_group_user_page(group_id, query)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def post(self, group_id, body: AddGroupUserSchema):
        """
        添加用户组成员
        :param group_id: 用户组ID
        :param body:
        :return:
        """
        return handler_add_user(group_id, body)

    @auth.login_required()
    @response_collect
    @validate()
    @casbin_enforcer.enforcer
    def put(self, group_id, body: UpdateGroupUserSchema):
        """
        编辑用户组的用户状态
        :param group_id: 用户组ID
        :param body:
        :return:
        """
        return handler_update_user(group_id, body)


class UserApplyGroup(Resource):
    @auth.login_required()
    @response_collect
    @validate()
    def post(self, group_id):
        """
        申请加入用户组
        :param group_id: 用户组ID
        :return:
        """
        return handler_apply_join_group(group_id)
