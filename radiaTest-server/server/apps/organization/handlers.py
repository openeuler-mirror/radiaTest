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
import re

from flask import request, jsonify, g
from sqlalchemy import or_

from server.model.administrator import Admin
from server.model.organization import Organization
from server.model.user import User
from server.model.group import Group, ReUserGroup
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.db import collect_sql_error
from server.schema.organization import OrgBaseSchema
from server.schema.base import PageBaseSchema
from server.schema.group import GroupInfoSchema


@collect_sql_error
def handler_org_group_page(org_id, query: PageBaseSchema):
    filter_params = [
        ReUserGroup.is_delete.is_(False),
        ReUserGroup.user_add_group_flag.is_(True),
        Group.is_delete.is_(False),
        ReUserGroup.org_id == org_id
    ]

    query_filter = ReUserGroup.query.join(Group).filter(*filter_params).order_by(
        ReUserGroup.create_time.desc(),
        ReUserGroup.id.asc()
    )

    def page_func(item):
        return GroupInfoSchema(**item.group.to_dict()).dict()

    # 返回结果
    page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(query_filter, func=page_func, is_set=True)
    if e:
        return jsonify(
            error_code=RET.SERVER_ERR,
            error_msg=f'get group under organization[{org_id}] info page error {e}'
        )
    return jsonify(
        error_code=RET.OK,
        error_msg=f"get group info under organization[{org_id}] is success",
        data=page_dict
    )


@collect_sql_error
def handler_get_all_org(query):
    filter_params = [
        Organization.is_delete == query.is_delete,
    ]
    if query.org_name:
        filter_params.append(Organization.name.like(f'%{query.org_name}%'))
    if query.org_description:
        filter_params.append(Organization.description.like(f'%{query.org_description}%'))

    query_filter = Organization.query.filter(*filter_params)

    def page_func(item):
        if item.is_delete:
            return None
        return OrgBaseSchema(**item.to_dict()).dict()

    page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(query_filter, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get organization page error {e}')

    return jsonify(error_code=RET.OK, error_msg="get organization page success", data=page_dict)


@collect_sql_error
def handler_org_user_page(org_id):
    admin = Admin.query.filter_by(account=g.user_login).first()
    if not admin:
        resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to get organization user info')
        return resp
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    group_id = request.args.get('group_id')

    # 获取组织下的所有用户
    filter_params = []
    if group_id:
        group_id = int(group_id)
        re_u_g = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
        user_ids = [item.user.user_id for item in re_u_g]
        filter_params.append(User.user_id.in_(user_ids))
    if name and len(str(name)) <= 255:
        name = re.escape(str(name))
        filter_params.append(or_(User.user_name.like(f'%{name}%'), User.user_login.like(f'%{name}%')))
    if not group_id and not name:
        filter_params.append(User.org_id == org_id)

    query_filter = User.query.filter(*filter_params)

    def page_func(item):
        user_dict = item.to_summary()
        return user_dict

    # 返回结果
    page_dict, e = PageUtil(page_num, page_size).get_page_dict(query_filter, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)
