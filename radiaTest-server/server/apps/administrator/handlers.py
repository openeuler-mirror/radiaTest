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

from flask import request, g, jsonify
from server import redis_client
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.auth_util import generate_token
from server.utils.db import collect_sql_error, Delete
from server.utils.file_util import FileUtil
from server.utils.cla_util import ClaShowAdminSchema
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import create_role, get_api, get_default_suffix
from server.model.administrator import Admin
from server.model.organization import Organization
from server.model.group import Group
from server.model.permission import Role, ReScopeRole, ReUserRole
from server.schema.organization import UpdateSchema


@collect_sql_error
def handler_login(body):
    # 从数据库中获取数据
    admin = Admin.query.filter_by(account=body.account).first()
    if not admin:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg='admin no find'
        )

    # 防止用户多次登录
    lock_key = f'admin_{request.remote_addr}_{admin.account}'
    i = redis_client.get(lock_key)
    if i and int(i) >= 5:
        return jsonify(
            error=RET.VERIFY_ERR,
            error_msg='login number is too many, account is locked'
        )

    if not admin.check_password_hash(body.password):
        redis_client.incr(lock_key)
        redis_client.expire(lock_key, ex=1800)
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='password error'
        )

    user_dict = {
        'gitee_id': f'admin_{admin.id}',
        'gitee_login': admin.account
    }
    redis_client.hmset(RedisKey.user(user_dict.get('gitee_id')), user_dict)
    token = generate_token(user_dict.get('gitee_id'), admin.account)
    return_dict = {
        'token': token
    }
    return jsonify(
        error_code=RET.OK,
        error_msg='OK',
        data=return_dict
    )


@collect_sql_error
def handler_register(body):
    if body.password != body.password2:
        return jsonify(
            error_code=RET.PARMA_ERR,
            error_msg='two passwords are inconsistent'
        )

    admin = Admin()
    admin.account = body.account
    admin.password = body.password
    admin_id = admin.add_flush_commit_id()
    if not admin_id:
        return jsonify(
            error_code=RET.DB_ERR,
            error_msg=f'database add error'
        )

    user_dict = {
        'gitee_id': f'admin_{admin_id}',
        'gitee_login': admin.account
    }
    redis_client.hmset(RedisKey.user(user_dict.get('gitee_id')), user_dict)
    token = generate_token(user_dict.get('gitee_id'), admin.account)
    return_dict = {
        'token': token,
    }
    return jsonify(
        error_code=RET.OK,
        error_msg='OK',
        data=return_dict
    )


@collect_sql_error
def handler_read_org_list():
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg='no right')
    org_list = Organization.query.filter_by(is_delete=False).all()
    cla_info_list = list()
    for item in org_list:
        cla_info_list.append(ClaShowAdminSchema(**item.to_dict()).dict())
    return jsonify(
        error_code=RET.OK,
        error_msg="OK",
        data=cla_info_list
    )


@collect_sql_error
def handler_save_org(body, avatar=None):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='no right'
        )

    # 添加一个新的组织
    org = Organization.query.filter_by(is_delete=False, name=body.name).first()
    if org:
        return jsonify(
            error_code=RET.DATA_EXIST_ERR,
            error_msg="organizations name exist"
        )

    if avatar is not None:
        avatar_url = FileUtil.flask_save_file(
            avatar,
            FileUtil.generate_filepath("avatar")
        )
        body.avatar_url = avatar_url

    org = Organization.create(body)
    if not org:
        return jsonify(
            error_code=RET.DB_ERR,
            error_msg="database add error"
        )
    # 角色初始化
    role_admin, role_list = create_role(_type='org', org=org)
    _data = {
        "permission_type": "org",
        "org_id": org.id
    }
    scope_data_allow, scope_data_deny = get_api("organization", "org.yaml", "org", org.id)
    PermissionManager().generate(scope_datas_allow=scope_data_allow, scope_datas_deny=scope_data_deny,
                                 _data=_data)

    for role in role_list:
        scope_data_allow, scope_data_deny = get_api("permission", "role.yaml", "role", role.id)
        PermissionManager().generate(scope_datas_allow=scope_data_allow, scope_datas_deny=scope_data_deny,
                                     _data=_data)
    return jsonify(
        error_code=RET.OK,
        error_msg="OK"
    )


@collect_sql_error
def handler_update_org(org_id):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='no right'
        )
    org = Organization.query.filter_by(is_delete=False, id=org_id).first()
    if not org:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg="the organization does not exist"
        )

    _form = dict()
    if request.form.get('is_delete'):
        org.is_delete = True
        flag = org.add_update()
        if not flag:
            return jsonify(
                error_code=RET.OTHER_REQ_ERR,
                error_msg='resources are related to current group, please delete these resources and retry!'
            )
    else:
        for key, value in request.form.items():
            if value:
                _form[key] = value
        body = UpdateSchema(**_form)
        avatar = request.files.get("avatar_url")
        if avatar:
            org.avatar_url = FileUtil.flask_save_file(
                avatar, org.avatar_url if org.avatar_url else FileUtil.generate_filepath('avatar'))
        else:
            org.avatar_url = None
        for key, value in body.dict().items():
            if hasattr(org, key) and (value or value is False):
                setattr(org, key, value)
    org.add_update()
    return jsonify(
        error_code=RET.OK,
        error_msg="OK"
    )


def delete_role(_type, org=None, group=None):
    filter_param = [Role.type == _type]
    if _type == 'org':
        filter_param.append(Role.org_id == org.id)
    elif _type == 'group':
        filter_param.append(Role.group_id == group.id)
    _roles = Role.query.filter(*filter_param).all()
    suffix = get_default_suffix(_type)
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
    sort_list[0].delete()
