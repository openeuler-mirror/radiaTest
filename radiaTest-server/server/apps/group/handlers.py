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

import json

from flask import request, g, jsonify
import sqlalchemy

from server import redis_client, db
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert, Delete
from server.utils.file_util import FileUtil, identify_file_type, FileTypeMapping
from server.utils.page_util import PageUtil
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import create_role, get_api
from server.model.group import Group, ReUserGroup, GroupRole
from server.model.administrator import Admin
from server.model.message import Message, MsgType, MsgLevel
from server.model.organization import Organization
from server.model.permission import ReUserRole, Role
from server.model.user import User
from server.schema.group import ReUserGroupSchema, GroupInfoSchema, QueryGroupUserSchema


@collect_sql_error
def handler_add_group():
    name = request.form.get('name')
    if not name:
        return jsonify(error_code=RET.PARMA_ERR, error_msg="group name is null")
    # 获取当前用户的组织id
    org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
    filter_params = [
        Group.name == name,
        Group.is_delete.is_(False),
        ReUserGroup.is_delete.is_(False),
        ReUserGroup.org_id == org_id
    ]
    re = ReUserGroup.query.join(Group).filter(*filter_params).first()
    if re:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="group has exists")
    avatar = request.files.get('avatar_url')
    if avatar:
        # 文件头检查
        verify_flag, res = identify_file_type(avatar, FileTypeMapping.image_type)
        if verify_flag is False:
            return res
    avatar_url = FileUtil.flask_save_file(avatar, FileUtil.generate_filepath('avatar'))
    description = request.form.get('description')
    # 创建一个group
    group_id, group = Group.create(name, description, avatar_url, g.user_id, org_id, 'org')
    # 创建用户和著之间的关系
    ReUserGroup.create(True, 1, g.user_id, group_id, org_id)

    # 初始化角色
    org = Organization.query.get(org_id)
    role_admin, role_list = create_role(_type='group', group=group, org=org)
    Insert(ReUserRole, {"user_id": g.user_id, "role_id": role_admin.id}).single()
    _data = {
        "permission_type": "group",
        "group_id": group_id
    }
    scope_data_allow, scope_data_deny = get_api("group", "group.yaml", "group", group_id)
    PermissionManager().generate(
        scope_datas_allow=scope_data_allow,
        scope_datas_deny=scope_data_deny,
        _data=_data
    )

    for role in role_list:
        scope_data_allow, scope_data_deny = get_api("permission", "role.yaml", "role", role.id)
        PermissionManager().generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data
        )

    return jsonify(
        error_code=RET.OK,
        error_msg="OK",
        data={"id": group_id}
    )


@collect_sql_error
def handler_update_group(group_id):
    # 获取参数
    name = request.json.get('name')
    avatar = request.files.get('avatar_url')
    description = request.json.get('description')
    if not name:
        return jsonify(error_code=RET.PARMA_ERR, error_msg="group name is null")
    # 从数据库中获取数据
    re = ReUserGroup.query.filter_by(group_id=group_id, user_id=g.user_id, is_delete=False).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"group no find")
    if re.role_type not in [GroupRole.admin.value, GroupRole.create_user.value]:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    group = re.group
    group.name = name
    group.description = description
    if avatar:
        # 文件头检查
        verify_flag, res = identify_file_type(avatar, FileTypeMapping.image_type)
        if verify_flag is False:
            return res
        group.avatar_url = FileUtil.flask_save_file(avatar, group.avatar_url)
    group.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_delete_group(group_id):
    re = ReUserGroup.query.filter_by(is_delete=False, user_id=g.user_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")

    # 创建者解散用户组
    if re.role_type == GroupRole.create_user.value:
        group = Group.query.filter_by(is_delete=False, id=group_id).first()
        if not group:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"group no find")
        group.is_delete = True
        flag = group.add_update()
        if not flag:
            return jsonify(
                error_code=RET.OTHER_REQ_ERR,
                error_msg='resources are related to current group, please delete these resources and retry!'
            )
        res = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
        org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
        Message.create_instance(json.dumps(
                        {
                            "info": f'<b>{org_name}'
                                    f'</b>组织下的<b>{re.group.name}</b>用户组已解散'
                        }
                    ), group_id, [item.user.user_id for item in res], org_id,
            level=MsgLevel.group.value, msg_type=MsgType.text.value)

        Group.query.filter_by(is_delete=False, id=group_id).update({'is_delete': True}, synchronize_session=False)
        ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).update({'is_delete': True},
                                                                               synchronize_session=False)

    # 用户组成员退出用户组
    elif re.role_type in [GroupRole.admin.value, GroupRole.user.value]:
        res = ReUserGroup.query.filter(ReUserGroup.is_delete.is_(False), ReUserGroup.group_id == group_id,
                                       ReUserGroup.role_type.in_([GroupRole.create_user.value, GroupRole.admin.value]),
                                       ReUserGroup.user_id != g.user_id).all()
        re.is_delete = True
        org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
        Message.create_instance(json.dumps(
                        {
                            "info": f'<b>{re.user.user_name}</b>退出'
                                    f'<b>{org_name}'
                                    f'</b>组织下的<b>{re.group.name}</b>用户组'
                        }
                    ), g.user_id, [item.user.user_id for item in res], org_id,
            level=MsgLevel.group.value, msg_type=MsgType.text.value)
        re.add_update()

        # 解除组内角色和用户的绑定
        _filter = [
            ReUserRole.user_id == g.user_id,
            Role.group_id == group_id,
            Role.type == 'group'
        ]
        re_list = ReUserRole.query.join(Role).filter(*_filter).all()
        for re in re_list:
            Delete(ReUserRole, {"id": re.id}).single()
    else:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_group_page():
    # 从数据库中获取当前用户所有的用户组
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    filter_params = [
        ReUserGroup.user_id == g.user_id,
        ReUserGroup.is_delete.is_(False),
        ReUserGroup.user_add_group_flag.is_(True),
        Group.is_delete.is_(False),
        ReUserGroup.org_id == redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
    ]
    if name:
        filter_params.append(Group.name.like(f"%{name}%"))

    query_filter = ReUserGroup.query.join(Group).filter(*filter_params).order_by(
        ReUserGroup.create_time.desc(),
        ReUserGroup.id.asc()
    )

    def page_func(item):
        re_dict = ReUserGroupSchema(**item.to_dict()).dict()
        group_dict = GroupInfoSchema(**item.group.to_dict()).dict()
        return {**re_dict, **group_dict}

    page_dict, e = PageUtil.get_page_dict(query_filter, page_num, page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_group_user_page(group_id, query: QueryGroupUserSchema):
    filter_params = [
        ReUserGroup.is_delete.is_(False),
        ReUserGroup.group_id == group_id,
        ReUserGroup.user_add_group_flag.is_(True),
    ]

    admin = Admin.query.filter_by(account=g.user_login).first()
    if not admin:
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        filter_params.append(ReUserGroup.org_id == org_id)

    if query.except_list:
        filter_params.append(
            ReUserGroup.user_id.notin_(query.except_list)
        )

    query_filter = ReUserGroup.query.filter(*filter_params) \
        .order_by(ReUserGroup.create_time.desc(), ReUserGroup.id.asc())

    # 获取用户组下的所有用户
    def page_func(item):
        user_dict = item.user.to_dict()
        re_dict = ReUserGroupSchema(**item.to_dict()).dict()
        return {**re_dict, **user_dict}

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_add_user(group_id, body):
    # 判断用户是否有权限
    re = ReUserGroup.query.filter_by(is_delete=False, user_id=g.user_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")
    if re.role_type not in [GroupRole.admin.value, GroupRole.create_user.value]:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")

    # 获取已在该用户组下的用户包含（待加入的）
    relations = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
    has_user_ids = [item.user.user_id for item in relations]
    # 创建新纪录但是不要添加到数据库
    add_list = list()
    org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
    org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
    for user_id in body.user_ids:
        if user_id in has_user_ids:
            continue
        add_list.append(dict(
            user_add_group_flag=False,
            role_type=0,
            user_id=user_id,
            group_id=int(group_id),
            org_id=org_id
        ))
        Message.create_instance(json.dumps(
                    {
                        "group_id": group_id,
                        "info": f'<b>{re.user.user_name}</b>邀请您加入'
                                f'<b>{org_name}</b>组织下的'
                                f'<b>{re.group.name}</b>用户组。'
                    }
                ), re.user.user_id, [user_id], org_id, level=MsgLevel.user.value, msg_type=MsgType.script.value)

    db.session.execute(ReUserGroup.__table__.insert(), add_list)
    db.session.commit()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_update_user(group_id, body):
    # 判断用户是否有权限
    re = ReUserGroup.query.filter_by(is_delete=False, user_id=g.user_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")
    if re.role_type in [GroupRole.admin.value, GroupRole.create_user.value]:
        filter_params = [
            ReUserGroup.user_id.in_(body.user_ids),
            ReUserGroup.group_id == group_id,
            ReUserGroup.is_delete.is_(False),
            ReUserGroup.user_add_group_flag.is_(True)
        ]
        if re.role_type == GroupRole.create_user.value:
            filter_params.append(ReUserGroup.role_type != GroupRole.create_user.value)
        else:
            filter_params.append(ReUserGroup.role_type.notin_([GroupRole.admin.value, GroupRole.create_user.value]))

        update_params = dict()
        if body.is_delete:
            res = ReUserGroup.query.filter(*filter_params).all()
            org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
            org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
            for item in res:
                user_id = item.user_id
                _filter = [ReUserRole.user_id == user_id,
                           Role.group_id == group_id,
                           Role.type == 'group']
                re_list = ReUserRole.query.join(Role).filter(*_filter).all()
                for _re in re_list:
                    Delete(ReUserRole, {"id": _re.id}).single()

                Message.create_instance(json.dumps(
                            {
                                'info': f'<b>{re.user.user_name}</b>将您请出'
                                        f'<b>{org_name}</b>组织下的'
                                        f'<b>{re.group.name}</b>用户组！'
                            }
                        ), g.user_id, [item.user_id], org_id, level=MsgLevel.user.value, msg_type=MsgType.text.value)
                item.delete()
        else:
            if body.role_type in [GroupRole.admin.value, GroupRole.user.value]:
                update_params["role_type"] = body.role_type
            ReUserGroup.query.filter(*filter_params).update(update_params, synchronize_session=False)
            db.session.commit()
    else:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_apply_join_group(group_id):
    group = Group.query.filter_by(id=group_id, is_delete=False).first()
    if not group:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group not find")
    re_exists = ReUserGroup.query.filter_by(user_id=g.user_id, group_id=group_id).first()
    if re_exists and re_exists.role_type == 0:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="你已申请加入组，请勿重复申请")

    re_info = ReUserGroup.query.filter(ReUserGroup.is_delete.is_(False), ReUserGroup.group_id == group_id,
                                       ReUserGroup.role_type.in_([1, 2])).all()
    org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
    user_info = User.query.filter_by(user_id=g.user_id).first()

    # 创建请求处理脚本消息
    apply_msg_info = json.dumps(
                {
                    "callback_url": '/api/v1/msg/addgroup/callback',
                    "group_id": group_id,
                    "group_name": group.name,
                    "info": f'<b>{user_info.user_name}</b>申请加入'
                            f'<b>{org_name}</b>组织下的'
                            f'<b>{group.name}</b>用户组。'
                }
            )
    Message.create_instance(apply_msg_info, g.user_id, [item.user_id for item in re_info], group.org_id,
                            level=MsgLevel.user.value, msg_type=MsgType.script.value)

    update_dict = dict(
        is_delete=False,
        user_add_group_flag=False,
        role_type=0,
        user_id=g.user_id,
        group_id=int(group_id),
        org_id=group.org_id
    )
    if re_exists and re_exists.is_delete:
        db.session.query(ReUserGroup).filter_by(id=re_exists.id).update(update_dict)
        db.session.commit()
    else:
        Insert(ReUserGroup, update_dict).single()

    # 申请通知消息
    notice_msg_info = json.dumps(
                {
                    'info': f'您申请加入'
                            f'<b>{org_name}</b>组织下的'
                            f'<b>{group.name}</b>用户组请求已发送，请求通过后将通知您'
                }
            )
    Message.create_instance(notice_msg_info, 1, [g.user_id], group.org_id, level=MsgLevel.system.value,
                            msg_type=MsgType.text.value)
    return jsonify(error_code=RET.OK, error_msg="申请已发送")


def handler_get_group_asset_rank(query):
    ranked_group = Group.query.filter(
        Group.rank != sqlalchemy.null(),
        Group.is_delete == False,
        Group.org_id == int(redis_client.hget(RedisKey.user(g.user_id), "current_org_id"))
    ).order_by(
        Group.rank.asc(),
        Group.create_time.asc(),
    )
    
    def page_func(item):
        group_dict = item.to_summary()
        return group_dict
    
    page_dict, e = PageUtil.get_page_dict(
            ranked_group, 
            query.page_num,
            query.page_size, 
            func=page_func
        )
    if e:
        return jsonify(
            error_code=RET.SERVER_ERR, 
            error_msg=f'get group rank page error: {e}'
        )
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)