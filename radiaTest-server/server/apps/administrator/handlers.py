from flask import request, g, jsonify
from server import redis_client
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.auth_util import generate_token
from server.utils.db import collect_sql_error
from server.utils.file_util import FileUtil
from server.utils.cla_util import ClaShowAdminSchema
from server.model.administrator import Admin
from server.model.organization import Organization


@collect_sql_error
def handler_login(body):
    # 从数据库中获取数据
    admin = Admin.query.filter_by(account=body.account).first()
    if not admin:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg='admin no find')

    # 防止用户多次登录
    lock_key = f'admin_{request.remote_addr}_{admin.account}'
    i = redis_client.get(lock_key)
    if i and int(i) >= 5:
        return jsonify(error=RET.VERIFY_ERR, error_msg='login number is too many, account is locked')

    if not admin.check_password_hash(body.password):
        redis_client.incr(lock_key)
        redis_client.expire(lock_key, ex=1800)
        return jsonify(error_code=RET.VERIFY_ERR, error_msg='password error')

    user_dict = {
        'gitee_id': f'admin_{admin.id}',
        'gitee_login': admin.account
    }
    redis_client.hmset(RedisKey.user(user_dict.get('gitee_id')), user_dict)
    token = generate_token(user_dict.get('gitee_id'), admin.account)
    return_dict = {
        'token': token
    }
    return jsonify(error_code=RET.OK, error_msg='OK', data=return_dict)


@collect_sql_error
def handler_register(body):
    if body.password != body.password2:
        return jsonify(error_code=RET.PARMA_ERR, error_msg='two passwords are inconsistent')

    admin = Admin()
    admin.account = body.account
    admin.password = body.password
    admin_id = admin.add_flush_commit_id()
    if not admin_id:
        return jsonify(error_code=RET.DB_ERR, error_msg=f'database add error')

    user_dict = {
        'gitee_id': f'admin_{admin_id}',
        'gitee_login': admin.account
    }
    redis_client.hmset(RedisKey.user(user_dict.get('gitee_id')), user_dict)
    token = generate_token(user_dict.get('gitee_id'), admin.account)
    return_dict = {
        'token': token,
    }
    return jsonify(error_code=RET.OK, error_msg='OK', data=return_dict)


@collect_sql_error
def handler_read_org_list():
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg='no right')
    org_list = Organization.query.filter_by(is_delete=False).all()
    cla_info_list = list()
    for item in org_list:
        cla_info_list.append(ClaShowAdminSchema(**item.to_dict()).dict())
    return jsonify(error_code=RET.OK, error_msg="OK", data=cla_info_list)


@collect_sql_error
def handler_save_org(body, avatar=None):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg='no right')

    # 添加一个新的组织
    org = Organization.query.filter_by(is_delete=False, name=body.name).first()
    if org:
        return jsonify(
            errno_code=RET.DATA_EXIST_ERR, 
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
        return jsonify(errno_code=RET.DB_ERR, error_msg="database add error")
    return jsonify(errno_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_update_org(org_id, body):
    # 判断用户是否为管理员
    admin = Admin.query.filter_by(account=g.gitee_login).first()
    if not admin:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg='no right')
    org = Organization.query.filter_by(is_delete=False, id=org_id).first()
    if not org:
        return jsonify(errno_code=RET.NO_DATA_ERR, error_msg="no find organization")
    for key, value in body.dict().items():
        if hasattr(org, key) and (value or value is False):
            setattr(org, key, value)
    org.add_update()
    return jsonify(errno_code=RET.OK, error_msg="OK")
