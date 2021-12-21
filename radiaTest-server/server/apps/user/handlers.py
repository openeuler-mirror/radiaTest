import json
from flask import current_app, request, Response, redirect, g, jsonify
from server import redis_client
from server.utils.response_util import RET
from server.utils.gitee_util import GiteeApi
from server.utils.auth_util import generate_token
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error
from server.utils.cla_util import Cla, ClaShowAdminSchema
from server.model.user import User
from server.model.message import Message
from server.model.organization import Organization, ReUserOrganization
from server.model.group import ReUserGroup, GroupRole
from server.schema.group import ReUserGroupSchema, GroupInfoSchema
from server.schema.organization import OrgUserInfoSchema, ReUserOrgSchema
from server.schema.user import UserInfoSchema


def handler_gitee_login():
    gitee_oauth_login_url = f"https://gitee.com/oauth/authorize?" \
                            f"client_id={current_app.config.get('GITEE_OAUTH_CLIENT_ID')}" \
                            f"&redirect_uri={current_app.config.get('GITEE_OAUTH_REDIRECT_URI')}" \
                            f"&response_type=code&scope={'%20'.join(current_app.config.get('GITEE_OAUTH_SCOPE'))}"
    return jsonify(error_code=RET.OK, error_msg='OK', data=gitee_oauth_login_url)


def handler_gitee_callback():
    # 校验参数
    code = request.args.get('code')
    if not code:
        return jsonify(error_code=RET.PARMA_ERR, error_msg="user code is not null")
    # 调用gitee的oauth授权接口
    oauth_flag, gitee_token = GiteeApi.Oauth.callback(code,
                                                      current_app.config.get("GITEE_OAUTH_CLIENT_ID"),
                                                      current_app.config.get("GITEE_OAUTH_REDIRECT_URI"),
                                                      current_app.config.get("GITEE_OAUTH_CLIENT_SECRET"))
    if not oauth_flag:
        return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg="gitee oauth request error")
    result = handler_login(gitee_token)
    if not isinstance(result, tuple) or not isinstance(result[0], bool):
        return result
    if result[0]:
        resp = Response()
        resp.headers['location'] = f'{current_app.config["GITEE_OAUTH_HOME_URL"]}?isSuccess=True'
        resp.status = 302
        resp.set_cookie('token', result[2])
        resp.set_cookie('gitee_id', str(result[1]))
        return resp
    else:
        return redirect(f'{current_app.config["GITEE_OAUTH_HOME_URL"]}?isSuccess=False&gitee_id={result[1]}')


@collect_sql_error
def handler_login(gitee_token):
    """
    处理用户登录
    :param gitee_token: gitee_token
    :return: 元组 (登录是否成功，gitee_id，[token，refresh_token])
             flask dict
    """
    # 调用gitee的api获取用户的基本信息
    user_flag, gitee_user = GiteeApi.User.get_info(gitee_token.get("access_token"))
    if not user_flag:
        return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg="gitee api request error")
    # 从数据库中获取用户信息
    user = User.query.filter_by(gitee_id=gitee_user.get("id")).first()
    # 判断用户是否存在
    if user:
        user = User.synchronize_gitee_info(gitee_user, user)
        # 用户缓存到redis中
        user.save_redis(gitee_token.get("access_token"), gitee_token.get("refresh_token"))
        # 生成token值
        token = generate_token(user.gitee_id, user.gitee_login)
        return True, user.gitee_id, token
    # 用户没有通过cla验证
    # 先将gitee的token缓存到redis中, 有效期为10min，这段时间主要用来是验证cla签名
    gitee_user["access_token"] = gitee_token.get("access_token")
    gitee_user["refresh_token"] = gitee_token.get("refresh_token")
    redis_client.hmset(RedisKey.gitee_user(gitee_user.get("id")), gitee_user, ex=600)
    # 返回结果
    return False, gitee_user.get("id")


@collect_sql_error
def handler_register(gitee_id, body):
    # 从redis中获取之前的gitee用户信息
    gitee_user = redis_client.hgetall(RedisKey.gitee_user(gitee_id))
    if not gitee_user:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user gitee info expired")
    # 从数据库中获取cla信息
    org = Organization.query.filter_by(id=body.organization_id, is_delete=False).first()
    if not org:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"database no find data")
    if not Cla.is_cla_signed(ClaShowAdminSchema(**org.to_dict()).dict(), body.cla_verify_params, body.cla_verify_body):
        return jsonify(error_code=RET.CLA_VERIFY_ERR, error_msg="user is not pass cla verification, please retry",
                       data=gitee_user.get("id"))
    # 生成用户和组织的关系
    re_user_organization = ReUserOrganization.create(gitee_user.get("id"), body.organization_id,
                                                     json.dumps({**body.cla_verify_params, **body.cla_verify_body}),
                                                     default=True)
    # 提取cla邮箱
    cla_email = None
    for key, value in {**body.cla_verify_params, **body.cla_verify_body}.items():
        if 'email' in key:
            cla_email = value
            break
    # 用户注册成功保存用户信息、生成token
    user = User.create_commit(gitee_user, cla_email, [re_user_organization])
    # 用户缓存到redis中
    user.save_redis(gitee_user.get("access_token"), gitee_user.get("refresh_token"), body.organization_id)
    redis_client.hset(RedisKey.user(gitee_user.get("id")), 'current_org_name', org.name)
    # 生成token值
    token = generate_token(user.gitee_id, user.gitee_login)
    return_data = {
        'token': token,
    }
    return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


@collect_sql_error
def handler_update_user(gitee_id, body):
    if g.gitee_id != gitee_id:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user token and user id do not match")
    # 从数据库中获取用户信息
    user = User.query.filter_by(gitee_id=gitee_id).first()
    if not user:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"user is no find")
    # 修改数据保存到数据库
    user.phone = body.phone
    user.add_update()
    # 修改缓存中的数据
    redis_client.hset(RedisKey.user(gitee_id), 'phone', body.phone)
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_user_info(gitee_id):
    if g.gitee_id != gitee_id:
        return jsonify(error_code=RET.VERIFY_ERR, error_msg="user token and user id do not match")
    user = User.query.filter_by(gitee_id=gitee_id).first()
    if not user:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"user is no find")
    user_dict = user.to_dict()
    # 用户组信息
    group_list = []
    groups = user.re_user_group
    if groups:
        for item in groups:
            re_user_group = ReUserGroupSchema(**item.to_dict())
            group = GroupInfoSchema(**item.group.to_dict())
            group_list.append({**re_user_group.dict(), **group.dict()})
    user_dict["groups"] = group_list
    # 组织信息
    org_list = []
    orgs = user.re_user_organization
    if orgs:
        for item in orgs:
            re_user_organization = ReUserOrgSchema(**item.to_dict())
            org = OrgUserInfoSchema(**item.organization.to_dict())
            org_list.append({**re_user_organization.dict(), **org.dict()})
    user_dict["orgs"] = org_list
    user_dict = UserInfoSchema(**user_dict).dict()
    return jsonify(error_code=RET.OK, error_msg="OK", data=user_dict)


def handler_logout():
    redis_client.delete(RedisKey.user(g.gitee_id))
    redis_client.delete(RedisKey.token(g.gitee_id))
    redis_client.delete(RedisKey.token(g.token))
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_select_default_org(org_id):
    # 从数据库中获取数据
    re = ReUserOrganization.query.filter_by(user_gitee_id=g.gitee_id, organization_id=org_id, is_delete=False).first()
    if not re:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="relationship no find")
    # 切换数据
    re_old = ReUserOrganization.query.filter_by(user_gitee_id=g.gitee_id, default=True, is_delete=False).first()
    if re_old:
        re_old.default = False
        re_old.add_update()
    re.default = True
    cla_email = None
    for key, value in json.loads(re.cla_info).items():
        if 'email' in key:
            cla_email = value
            break
    user = re.user
    user.cla_email = cla_email
    re.add_update()
    user.add_update()
    redis_client.hset(RedisKey.user(g.gitee_id), 'current_org_id', org_id)
    redis_client.hset(RedisKey.user(g.gitee_id), 'current_org_name', re.organization.name)
    return jsonify(error_code=RET.OK, error_msg="OK")


def handler_add_group(group_id, body):
    re = ReUserGroup.query.filter_by(user_gitee_id=g.gitee_id, group_id=group_id, is_delete=False).first()
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False).first()
    if not re or not msg:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="relationship no find")
    if re.user_add_group_flag or re.role_type == GroupRole.user.value:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="relationship is exist")
    info = f'<b>{re.user.gitee_name}</b>{{}}' \
           f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "current_org_name")}' \
           f'</b>组织下<b>{re.group.name}</b>用户组'
    if body.access:
        re.user_add_group_flag = True
        re.role_type = GroupRole.user.value
        info = info.format('已加入')
        message = Message.create_instance(dict(info=info), g.gitee_id, msg.from_id)
        message1 = Message.create_instance(dict(info=info), g.gitee_id, g.gitee_id)
    else:
        re.is_delete = True
        info = info.format('拒绝加入')
        message = Message.create_instance(dict(info=info), g.gitee_id, msg.from_id)
        message1 = Message.create_instance(dict(info=info), g.gitee_id, g.gitee_id)
    msg.is_delete = True
    re.add_update()
    message.add_update()
    message1.add_update()
    msg.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")

# def handler_token(re_token):
#     # 判断refresh是否过期
#     token_data = redis_client.get(RedisKey.refresh_token(re_token))
#     if not token_data:
#         return jsonify(error_code=RET.VERIFY_ERR, error_msg="user login expired")
#     token_data = json.loads(token_data)
#     # 删除原来的refresh_token
#     redis_client.delete(RedisKey.refresh_token(re_token))
#     redis_client.delete(RedisKey.token(token_data.get("gitee_id")))
#     token, refresh_token = generate_token(token_data.get("gitee_id"), token_data.get("gitee_login"))
#     return_data = {
#         'token': token, 'refresh_token': refresh_token
#     }
#     return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)
