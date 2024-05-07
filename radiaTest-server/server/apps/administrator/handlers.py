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
# @Date    : 2022/12/26
# @License : Mulan PSL v2


#####################################
from datetime import datetime
import pytz

from flask import request, g, jsonify, current_app

from server import db
from server import redis_client
from server.utils.response_util import RET, log_util
from server.utils.redis_util import RedisKey
from server.utils.auth_util import generate_token
from server.utils.db import collect_sql_error, Delete
from server.utils.file_util import FileUtil, identify_file_type, FileTypeMapping
from server.utils.permission_utils import PermissionManager
from server.utils.read_from_yaml import create_role, get_api, get_default_suffix
from server.model.administrator import Admin
from server.model.organization import Organization
from server.model.permission import Role, ReScopeRole, ReUserRole
from server.schema.organization import UpdateSchema


@collect_sql_error
def handler_login(body):
    # 从数据库中获取数据
    admin = Admin.query.filter_by(account=body.account).first()
    if not admin:
        resp = jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='Account does not exist or password is incorrect. Please re-enter'
        )
        log_util(resp)
        return resp
    # 防止用户多次登录
    lock_key = f'admin_{request.remote_addr}_{admin.account}'
    i = redis_client.get(lock_key)
    if i and int(i) >= 5:
        resp = jsonify(
            error=RET.VERIFY_ERR,
            error_msg='login number is too many, account is locked'
        )
        log_util(resp)
        return resp

    if not admin.check_password_hash(body.password):
        redis_client.incr(lock_key)
        redis_client.expire(lock_key, ex=1800)
        resp = jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='Account does not exist or password is incorrect. Please re-enter'
        )
        log_util(resp)
        return resp

    user_dict = {
        'user_id': f'admin_{admin.id}',
        'user_login': admin.account
    }
    redis_client.hmset(RedisKey.oauth_user(user_dict.get('user_id')), user_dict)
    token = generate_token(
        user_dict.get('user_id'),
        admin.account,
        int(current_app.config.get("LOGIN_EXPIRES_TIME"))
    )

    pwd_reset_flag = 0
    if admin.last_login_time == datetime(year=1970, month=1, day=1):
        pwd_reset_flag = 1
    else:
        admin.last_login_time = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        admin.add_update(Admin, '/admin')

    return_dict = {
        'token': token,
        'admin': 1,
        'account': admin.account,
        'password_need_reset': pwd_reset_flag
    }

    body.password = ""
    resp = jsonify(
        error_code=RET.OK,
        error_msg='admin login success',
        data=return_dict
    )
    log_util(resp)
    return resp


@collect_sql_error
def handler_read_org_list():
    admin = Admin.query.filter_by(account=g.user_login).first()
    if not admin:
        resp = jsonify(error_code=RET.VERIFY_ERR, error_msg='user no right to get organization info')
        return resp
    org_list = Organization.query.filter_by(is_delete=False).all()
    org_info_list = list()
    for item in org_list:
        org_info_list.append(item.to_dict())
    resp = jsonify(
        error_code=RET.OK,
        error_msg="admin get organization success",
        data=org_info_list
    )
    return resp


@collect_sql_error
def handler_save_org(body, avatar=None):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.user_login).first()
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
            error_msg="database add organization error"
        )
    # 角色初始化
    role_admin, role_list = create_role(_type='org', org=org)
    _data = {
        "permission_type": "org",
        "org_id": org.id
    }
    scope_data_allow, scope_data_deny = get_api("organization", "org.yaml", "org", org.id)
    PermissionManager(org_id=org.id).generate(
        scope_datas_allow=scope_data_allow,
        scope_datas_deny=scope_data_deny,
        _data=_data
    )

    for role in role_list:
        scope_data_allow, scope_data_deny = get_api("permission", "role.yaml", "role", role.id)
        PermissionManager(org_id=org.id).generate(
            scope_datas_allow=scope_data_allow,
            scope_datas_deny=scope_data_deny,
            _data=_data
        )
    return jsonify(
        error_code=RET.OK,
        error_msg="organization create success",
        data={"id": org.id}
    )


@collect_sql_error
def handler_update_org(org_id):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.user_login).first()
    if not admin:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='user no right to update organizaton'
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
        db.session.add(org)
        db.session.commit()
    else:
        for key, value in request.form.items():
            if value:
                _form[key] = value

        result, form = check_authority(_form)
        if not result:
            return form

        body = UpdateSchema(**form)
        avatar = request.files.get("avatar_url")

        if avatar:
            # 文件头检查
            verify_flag, res = identify_file_type(avatar, FileTypeMapping.image_type)
            if verify_flag is False:
                return res
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
        error_msg="update organization info success"
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


@collect_sql_error
def handler_change_passwd(body):
    admin = Admin.query.filter_by(account=body.account).first()
    if not admin:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg='admin not find'
        )

    lock_key = f'admin_change_{request.remote_addr}_{admin.account}'
    i = redis_client.get(lock_key)
    if i and int(i) >= 5:
        redis_client.delete(RedisKey.user(g.user_id))
        redis_client.delete(RedisKey.token(g.user_id))
        redis_client.delete(RedisKey.token(g.token))
        return jsonify(
            error=RET.OK,
            error_msg='change password number is too many, account is locked'
        )

    if not admin.check_password_hash(body.old_password):
        redis_client.incr(lock_key)
        redis_client.expire(lock_key, ex=1800)
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg='Account does not exist or password is incorrect. Please re-enter'
        )
    admin.password = body.new_password
    admin.last_login_time = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
    admin.add_update(Admin, '/admin')
    redis_client.delete(RedisKey.user(g.user_id))
    redis_client.delete(RedisKey.token(g.user_id))
    redis_client.delete(RedisKey.token(g.token))
    body.old_password = ""
    body.new_password = ""
    return jsonify(
        error_code=RET.OK,
        error_msg="admin new password update success"
    )


def check_authority(form: dict):
    if form.get("authority") == "default":
        if not all((
                current_app.config.get("GITEE_OAUTH_CLIENT_ID"),
                current_app.config.get("GITEE_OAUTH_CLIENT_SECRET"),
                current_app.config.get("GITEE_OAUTH_LOGIN_URL"),
                current_app.config.get("GITEE_OAUTH_GET_TOKEN_URL"),
                current_app.config.get("GITEE_OAUTH_GET_USER_INFO_URL"),
                current_app.config.get("GITEE_OAUTH_SCOPE")
        )):
            return False, jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="default config is not complete",
            )
        else:
            form.update({
                "authority": "gitee",
                "oauth_client_id": current_app.config.get("GITEE_OAUTH_CLIENT_ID"),
                "oauth_client_secret": current_app.config.get("GITEE_OAUTH_CLIENT_SECRET"),
                "oauth_login_url": current_app.config.get("GITEE_OAUTH_LOGIN_URL"),
                "oauth_get_token_url": current_app.config.get("GITEE_OAUTH_GET_TOKEN_URL"),
                "oauth_get_user_info_url": current_app.config.get("GITEE_OAUTH_GET_USER_INFO_URL"),
                "oauth_scope": current_app.config.get("GITEE_OAUTH_SCOPE")
            })
    return True, form
