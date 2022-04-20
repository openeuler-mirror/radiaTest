# Copyright (c) [2021] Huawei Technologies Co.,Ltd.ALL rights reserved.
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

from flask import request, g, current_app, jsonify

from server import redis_client, db
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert, Delete
from server.utils.file_util import FileUtil
from server.utils.page_util import PageUtil
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import create_role, get_default_suffix, get_api
from server.model.group import Group, ReUserGroup, GroupRole
from server.model.administrator import Admin
from server.model.message import Message, MsgType, MsgLevel
from server.model.organization import Organization
from server.model.permission import ReUserRole, Role, ReScopeRole
from server.schema.group import ReUserGroupSchema, GroupInfoSchema, QueryGroupUserSchema


@collect_sql_error
def handler_add_group():
    name = request.form.get('name')
    if not name:
        return jsonify(error_code=RET.PARMA_ERR, error_msg="group name is null")
    # 获取当前用户的组织id
    org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
    filter_params = [
        Group.name == name,
        Group.is_delete == False,
        ReUserGroup.is_delete == False,
        ReUserGroup.org_id == org_id
    ]
    re = ReUserGroup.query.join(Group).filter(*filter_params).first()
    if re:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="group has exists")
    avatar = request.files.get('avatar_url')
    avatar_url = FileUtil.flask_save_file(avatar, FileUtil.generate_filepath('avatar'))
    description = request.form.get('description')
    # 创建一个group
    group_id, group = Group.create(name, description, avatar_url, g.gitee_id, org_id, 'org')
    # 创建用户和著之间的关系
    ReUserGroup.create(True, 1, g.gitee_id, group_id, org_id)

    # 初始化角色
    org = Organization.query.get(org_id)
    role_admin, role_list = create_role(_type='group', group=group, org=org)
    Insert(ReUserRole, {"user_id": g.gitee_id, "role_id": role_admin.id}).single()
    _data = {
        "permission_type": "group",
        "group_id": group_id
    }
    scope_data_allow, scope_data_deny = get_api("group", "group.yaml", "group", group_id)
    PermissionManager().generate(scope_datas_allow=scope_data_allow, scope_datas_deny=scope_data_deny,
                                 _data=_data)
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_update_group(group_id):
    # 获取参数
    name = request.json.get('name')
    avatar = request.files.get('avatar_url')
    description = request.json.get('description')
    if not name:
        return jsonify(error_code=RET.PARMA_ERR, error_msg="group name is null")
    # 从数据库中获取数据
    re = ReUserGroup.query.filter_by(group_id=group_id, user_gitee_id=g.gitee_id, is_delete=False).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"group no find")
    if re.role_type not in [GroupRole.admin.value, GroupRole.create_user.value]:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    group = re.group
    group.name = name
    group.description = description
    if avatar:
        group.avatar_url = FileUtil.flask_save_file(avatar, group.avatar_url)
    group.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_delete_group(group_id):
    re = ReUserGroup.query.filter_by(is_delete=False, user_gitee_id=g.gitee_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")

    msg_list = list()

    # 创建者解散用户组
    if re.role_type == GroupRole.create_user.value:
        res = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
        for item in res:
            msg_list.append({
                'from_id': group_id,
                'to_id': item.user.gitee_id,
                'data': json.dumps(dict(info=f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")}'
                                             f'</b>组织下的<b>{re.group.name}</b>用户组已解散')),
                'level': MsgLevel.group.value
            })
        Group.query.filter_by(is_delete=False, id=group_id).update({'is_delete': True}, synchronize_session=False)
        ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).update({'is_delete': True},
                                                                               synchronize_session=False)

        _roles = Role.query.filter_by(type='group', group_id=group_id).all()
        suffix = get_default_suffix('group')
        sort_list = []
        for _role in _roles:
            if _role.name == suffix:
                sort_list.insert(0, _role)
            else:
                sort_list.append(_role)
        for _role in sort_list:
            _urs = ReUserRole.query.filter_by(role_id=_role.id).all()
            _srs = ReScopeRole.query.filter_by(role_id=_role.id).all()
            for _re in _urs:
                Delete(ReUserRole, {"id": _re.id}).single()
            for _re in _srs:
                Delete(ReScopeRole, {"id": _re.id}).single()
        for _role in sort_list:
            _role.delete()

    # 用户组成员退出用户组
    elif re.role_type in [GroupRole.admin.value, GroupRole.user.value]:
        res = ReUserGroup.query.filter(ReUserGroup.is_delete == False, ReUserGroup.group_id == group_id,
                                       ReUserGroup.role_type.in_([GroupRole.create_user.value, GroupRole.admin.value]),
                                       ReUserGroup.user_gitee_id != g.gitee_id).all()
        re.is_delete = True
        for item in res:
            msg_list.append({
                'from_id': g.gitee_id,
                'to_id': item.user.gitee_id,
                'data': json.dumps(dict(info=f'<b>{re.user.gitee_name}</b>退出'
                                             f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")}'
                                             f'</b>组织下的<b>{re.group.name}</b>用户组'))
            })
        re.add_update()

        # 解除组内角色和用户的绑定
        _filter = [ReUserRole.user_id == g.gitee_id,
            Role.group_id == group_id,
            Role.type == 'group']
        re_list = ReUserRole.query.join(Role).filter(*_filter).all()
        for re in re_list:
            Delete(ReUserRole, {"id": re.id}).single()
    else:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    db.session.execute(Message.__table__.insert(), msg_list)
    db.session.commit()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_group_page():
    # 从数据库中获取当前用户所有的用户组
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    filter_params = [
        ReUserGroup.user_gitee_id == g.gitee_id,
        ReUserGroup.is_delete == False,
        ReUserGroup.user_add_group_flag == True,
        Group.is_delete == False,
        ReUserGroup.org_id == redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
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

    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        filter_params.append(ReUserGroup.org_id == org_id)

    if query.except_list:
        filter_params.append(
            ReUserGroup.user_gitee_id.notin_(query.except_list)
        )

    query_filter = ReUserGroup.query.filter(*filter_params).order_by(ReUserGroup.create_time.desc())

    # 获取用户组下的所有用户
    def page_func(item):
        if item.is_delete:
            return None
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
    re = ReUserGroup.query.filter_by(is_delete=False, user_gitee_id=g.gitee_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")
    if re.role_type not in [GroupRole.admin.value, GroupRole.create_user.value]:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")

    # 获取已在该用户组下的用户包含（待加入的）
    relations = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
    has_gitee_ids = [item.user.gitee_id for item in relations]
    # 创建新纪录但是不要添加到数据库
    add_list = list()
    message_list = list()
    for gitee_id in body.gitee_ids:
        if gitee_id in has_gitee_ids:
            continue
        add_list.append(dict(
            user_add_group_flag=False,
            role_type=0,
            user_gitee_id=int(gitee_id),
            group_id=int(group_id),
            org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        ))
        message_list.append(dict(
            data=json.dumps(
                dict(group_id=group_id,
                     info=f'<b>{re.user.gitee_name}</b>邀请您加入'
                          f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")}</b>组织下的'
                          f'<b>{re.group.name}</b>用户组。')),
            level=MsgLevel.user.value,
            from_id=re.user.gitee_id,
            to_id=gitee_id,
            type=MsgType.script.value
        ))
    db.session.execute(ReUserGroup.__table__.insert(), add_list)
    db.session.execute(Message.__table__.insert(), message_list)
    db.session.commit()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_update_user(group_id, body):
    # 判断用户是否有权限
    re = ReUserGroup.query.filter_by(is_delete=False, user_gitee_id=g.gitee_id, group_id=group_id).first()
    if not re or re.group.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user group no find")
    if re.role_type in [GroupRole.admin.value, GroupRole.create_user.value]:
        filter_params = [
            ReUserGroup.user_gitee_id.in_(body.gitee_ids),
            ReUserGroup.group_id == group_id,
            ReUserGroup.is_delete == False,
            ReUserGroup.user_add_group_flag == True
        ]
        if re.role_type == GroupRole.create_user.value:
            filter_params.append(ReUserGroup.role_type != GroupRole.create_user.value)
        else:
            filter_params.append(ReUserGroup.role_type.notin_([GroupRole.admin.value, GroupRole.create_user.value]))

        update_params = dict()
        if body.is_delete:
            update_params["is_delete"] = body.is_delete
            res = ReUserGroup.query.filter(*filter_params).all()
            msg_list = list()
            for item in res:
                msg_list.append(dict(
                    data=json.dumps(
                        dict(info=f'<b>{re.user.gitee_name}</b>将您请出'
                                  f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")}</b>组织下的'
                                  f'<b>{re.group.name}</b>用户组！')),
                    level=MsgLevel.user.value,
                    from_id=g.gitee_id,
                    to_id=item.user_gitee_id,
                    type=MsgType.text.value
                ))
            db.session.execute(Message.__table__.insert(), msg_list)
            db.session.commit()

        if body.role_type in [GroupRole.admin.value, GroupRole.user.value]:
            update_params["role_type"] = body.role_type
        ReUserGroup.query.filter(*filter_params).update(update_params, synchronize_session=False)
        db.session.commit()
    else:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user has not right")
    return jsonify(error_code=RET.OK, error_msg="OK")
