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
from datetime import datetime, timedelta
import pytz
from flask import current_app, request, Response, redirect, g, jsonify
from sqlalchemy import or_, and_, extract

from server import redis_client
from server.utils.response_util import RET
from server.utils.oauth_util import LoginApi
from server.utils.auth_util import generate_token
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert
from server.utils.read_from_yaml import get_default_suffix
from server.model.user import User
from server.model.message import Message, MessageInstance
from server.model.task import Task
from server.model.milestone import Milestone
from server.model.organization import Organization
from server.model.group import ReUserGroup, GroupRole
from server.model.permission import Role, ReUserRole
from server.schema.group import ReUserGroupSchema, GroupInfoSchema
from server.schema.user import UserInfoSchema, UserTaskSchema
from server.schema.task import TaskInfoSchema
from server.utils.page_util import PageUtil
from server.utils.scope_util import ScopeKey
from server.utils.user_util import ProfileMap


def handler_oauth_login(query):
    org = Organization.query.filter_by(id=query.org_id, is_delete=0).first()
    if not org:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg="the organization not exist"
        )

    return handler_oauth_login_url(org)


def handler_oauth_login_url(org: Organization):
    deal_scope = getattr(ScopeKey, org.authority)
    oauth_login_url = "{}?client_id={}&redirect_uri={}&response_type=code&scope={}".format(
        current_app.config.get("OAUTH_LOGIN_URL"),
        current_app.config.get("OAUTH_CLIENT_ID"),
        current_app.config.get("OAUTH_REDIRECT_URI"),
        deal_scope(current_app.config.get("OAUTH_SCOPE"))
    )
    return jsonify(
        error_code=RET.OK,
        error_msg='OK',
        data=oauth_login_url
    )


def handler_oauth_callback():
    # 校验参数
    code = request.args.get('code')
    if not code:
        return jsonify(
            error_code=RET.PARMA_ERR,
            error_msg="user code should not be null"
        )

    return redirect(
        '{}?code={}'.format(
            current_app.config["OAUTH_HOME_URL"],
            code
        )
    )


def handler_login_callback(query):
    # 校验参数
    org = Organization.query.filter_by(id=query.org_id, is_delete=0).first()
    if not org:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg="the organization not exist"
        )

    oauth_flag, oauth_token = LoginApi.Oauth.callback(
        current_app.config.get("OAUTH_GET_TOKEN_URL"),
        query.code,
        current_app.config.get("OAUTH_CLIENT_ID"),
        current_app.config.get("OAUTH_REDIRECT_URI"),
        current_app.config.get("OAUTH_CLIENT_SECRET")
    )

    if not oauth_flag:
        return jsonify(
            error_code=RET.OTHER_REQ_ERR,
            error_msg="oauth request error"
        )

    result = handler_login(
        oauth_token,
        org.id,
        current_app.config.get("OAUTH_GET_USER_INFO_URL"),
        current_app.config.get("AUTHORITY"),
        org.name
    )
    if not isinstance(result, dict):
        return result

    resp = Response(content_type="application/json")
    resp.set_data(
        json.dumps(
            {
                "error_code": RET.OK,
                "error_msg": "OK",
                "data": {
                    "url": f'{current_app.config["OAUTH_HOME_URL"]}?isSuccess=True',
                    "user_id": result.get("user_id"),
                    "token": result.get("token"),
                    "current_org_id": result.get("org_id"),
                    "current_org_name": result.get("org_name")
                }
            }
        )
    )
    resp.status = 200
    return resp


@collect_sql_error
def handler_login(oauth_token, org_id, oauth_user_info_url, authority, org_name):
    """
    处理用户登录
    :param oauth_token: oauth_token
    :param org_id: 当前登入的组织id
    :param oauth_user_info_url: 鉴权机构的获取用户信息url
    :param authority: 鉴权机构
    :param org_name: 当前登录的组织名
    :return: 元组 (登录是否成功，user_id，[token，refresh_token])
             flask dict
    """
    # 调用鉴权服务指定的api获取用户的基本信息
    user_flag, oauth_user = LoginApi.User.get_info(
        oauth_user_info_url,
        oauth_token.get("access_token"),
        authority
    )
    if not user_flag:
        return jsonify(
            error_code=RET.OTHER_REQ_ERR,
            error_msg="get user info request error"
        )

    profile_map = getattr(ProfileMap, authority)
    profile = profile_map(oauth_user)
    redis_client.hmset(
        RedisKey.oauth_user(profile.get("user_id")),
        profile,
        ex=int(current_app.config.get("LOGIN_EXPIRES_TIME")),
    )

    # 从数据库中获取用户信息
    user = User.query.filter_by(user_id=profile.get("user_id")).first()
    # 判断用户是否存在
    if user:
        current_org_id = user.org_id
        current_org = Organization.query.filter_by(id=current_org_id).first()
        if not current_org:
            current_org_name = ""
        else:
            current_org_name = current_org.name
        user = User.synchronize_oauth_info(profile, user)
    else:
        user = User.create_commit(profile, org_id)
        current_org_id = org_id
        current_org_name = org_name

    _resp = handler_select_default_org(current_org_id, current_org_name, user.user_id)
    _r = None
    try:
        _r = _resp.json
    except (AttributeError, TypeError) as e:
        raise RuntimeError(str(e)) from e
    if _r.get("error_code") != RET.OK:
        return _resp
    handler_register(user.user_id, org_id)
    # 生成token值
    token = generate_token(
        user.user_id,
        user.user_login,
        int(current_app.config.get("LOGIN_EXPIRES_TIME"))
    )

    return {
        "user_id": user.user_id,
        "token": token,
        "org_id": current_org_id,
        "org_name": current_org_name
    }


@collect_sql_error
def handler_register(user_id, org_id):
    _role = Role.query.filter_by(name=user_id, type='person').first()
    if not _role:
        role = Role(name=user_id, type='person')
        role_id = role.add_flush_commit_id()
        Insert(ReUserRole, {"user_id": user_id, "role_id": role_id}).single()

    # 绑定用户和组织基础角色、公共基础角色的关系
    org_suffix = get_default_suffix('org')
    public_suffix = get_default_suffix('public')
    filter_params = [
        or_(
            and_(
                Role.org_id == org_id,
                Role.type == 'org',
                Role.name == org_suffix
            ),
            and_(
                Role.type == 'public',
                Role.name == public_suffix
            )
        )
    ]
    roles = Role.query.filter(*filter_params).all()
    for _role in roles:
        re_user_role = ReUserRole.query.filter_by(user_id=user_id, role_id=_role.id).first()
        if not re_user_role:
            Insert(ReUserRole, {"user_id": user_id, "role_id": _role.id}).single()


@collect_sql_error
def handler_user_info(user_id):
    if g.user_id != user_id:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg="user token and user id do not match"
        )

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"user is no find")
    user_dict = user.to_json()
    # 用户组信息
    group_list = []
    groups = user.re_user_group
    if groups:
        for item in groups:
            re_user_group = ReUserGroupSchema(**item.to_dict())
            group = GroupInfoSchema(**item.group.to_dict())
            if not group.is_delete:
                group_list.append({**re_user_group.dict(), **group.dict()})
    user_dict["groups"] = group_list

    # 组织信息
    org_list = []
    user_dict["orgs"] = org_list
    user_dict = UserInfoSchema(**user_dict).dict()
    return jsonify(error_code=RET.OK, error_msg="OK", data=user_dict)


def handler_logout():
    redis_client.delete(RedisKey.user(g.user_id))
    redis_client.delete(RedisKey.token(g.user_id))
    redis_client.delete(RedisKey.token(g.token))
    current_user = g.user_id
    if current_user.startswith("admin_"):
        return jsonify(
            error_code=RET.OK
        )
    return jsonify(
        error_code=RET.OK,
        error_msg="{}?client_id={}&redirect_uri={}".format(
            current_app.config.get("OAUTH_LOGOUT"),
            current_app.config.get("CLIENT_ID"),
            current_app.config.get("HOME_PAGE")
        )
    )


@collect_sql_error
def handler_select_default_org(org_id, org_name, user_id=None):
    if user_id is None:
        user_oauth_id = g.user_id
    else:
        user_oauth_id = user_id
    try:
        redis_client.hset(
            RedisKey.user(user_oauth_id),
            'current_org_id',
            org_id
        )
        redis_client.hset(
            RedisKey.user(user_oauth_id),
            'current_org_name',
            org_name
        )
        return jsonify(error_code=RET.OK, error_msg="OK")
    except Exception as e:
        return jsonify(error_code=RET.OTHER_REQ_ERR, error_msg="something error happened")


def handler_add_group(group_id, body):
    re = ReUserGroup.query.filter_by(user_id=g.user_id, group_id=group_id, is_delete=False).first()
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False).first()
    if not re or not msg:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg=f"handler add group failed due to user[{g.user_id}] or message[{body.msg_id}] is not exists"
        )
    if re.user_add_group_flag or re.role_type == GroupRole.user.value:
        return jsonify(
            error_code=RET.DATA_EXIST_ERR,
            error_msg=f"handler add group failed due to user[{g.user_id}] and group[{group_id}] is exists"
        )
    info = f'<b>{re.user.user_name}</b>{{}}' \
           f'<b>{redis_client.hget(RedisKey.user(g.user_id), "current_org_name")}' \
           f'</b>组织下<b>{re.group.name}</b>用户组'
    if body.access:
        re.user_add_group_flag = True
        re.role_type = GroupRole.user.value
        info = info.format('已加入')
        message_instance = MessageInstance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
        message_instance1 = MessageInstance(dict(info=info), g.user_id, g.user_id, msg.org_id)
        message = Message.create_instance(message_instance)
        message1 = Message.create_instance(message_instance1)

        # 绑定用户和用户组基础角色关系
        group_suffix = get_default_suffix('group')
        filter_params = [
            Role.group_id == group_id,
            Role.type == 'group',
            Role.name == group_suffix
        ]
        role = Role.query.filter(*filter_params).first()
        Insert(ReUserRole, {"user_id": g.user_id, "role_id": role.id}).single()
    else:
        re.is_delete = True
        info = info.format('拒绝加入')
        message_instance = MessageInstance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
        message_instance1 = MessageInstance(dict(info=info), g.user_id, g.user_id, msg.org_id)
        message = Message.create_instance(message_instance)
        message1 = Message.create_instance(message_instance1)
    msg.is_delete = True
    re.add_update()
    message.add_update()
    message1.add_update()
    msg.add_update()
    return jsonify(error_code=RET.OK, error_msg="handler user add group success")


@collect_sql_error
def handler_get_all(query):
    filter_params = []

    if query.user_id:
        filter_params.append(User.user_id.like(f'%{query.user_id}%'))
    if query.user_login:
        filter_params.append(User.user_login.like(f'%{query.user_login}%'))
    if query.user_name:
        filter_params.append(User.user_name.like(f'%{query.user_name}%'))

    query_filter = User.query.filter(*filter_params).order_by(User.create_time.desc(), User.user_id.asc())

    # 获取用户组下的所有用户
    def page_func(item):
        user_dict = item.to_json()
        return user_dict

    # 返回结果
    page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(query_filter, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_get_user_task(query: UserTaskSchema):
    current_org_id = int(redis_client.hget(
        RedisKey.user(g.user_id),
        'current_org_id'
    ))
    now = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
    # 全部任务
    basic_filter_params = [Task.is_delete.is_(False), Task.executor_id == g.user_id, Task.org_id == current_org_id]

    # 今日任务总数
    today_filter_params = [
        extract('year', Task.create_time) == now.year,
        extract('month', Task.create_time) == now.month,
        extract('day', Task.create_time) == now.day
    ]
    today_filter_params.extend(basic_filter_params)
    today_tasks_count = Task.query.filter(*today_filter_params).count()

    # 本周任务总数
    today = datetime(now.year, now.month, now.day, 0, 0, 0)
    this_week_start = today - timedelta(days=now.weekday())
    this_week_end = today + timedelta(days=7 - now.weekday())
    week_filter_params = [Task.create_time >= this_week_start, Task.create_time < this_week_end]
    week_filter_params.extend(basic_filter_params)
    week_tasks_count = Task.query.filter(*week_filter_params).count()

    # 本月任务总数
    this_month_start = datetime(now.year, now.month, 1)
    if now.month < 12:
        next_month_start = datetime(now.year, now.month + 1, 1)
    else:
        next_month_start = datetime(now.year + 1, 1, 1)

    month_filter_params = [Task.create_time >= this_month_start, Task.create_time < next_month_start]
    month_filter_params.extend(basic_filter_params)
    month_tasks_count = Task.query.filter(*month_filter_params).count()

    def page_func(task: Task):
        item_dict = TaskInfoSchema(**task.__dict__).dict()
        if task.type != 'VERSION' and task.milestones:
            milestone = Milestone.query.get(task.milestones[0].milestone_id) if task.milestones else None
            item_dict['milestone'] = milestone.to_json()
        elif task.type == 'VERSION' and task.milestones:
            milestones = [item.milestone_id for item in task.milestones]
            milestones = Milestone.query.filter(Milestone.id.in_(milestones)).all()
            item_dict['milestones'] = [item.to_json() for item in milestones]
        return item_dict

    if query.task_title:
        basic_filter_params.append(Task.title.like(f'%{query.task_title}%'))

    filter_param = []
    if query.task_type == 'all':
        # 任务总数、分页
        basic_filter = Task.query.filter(*basic_filter_params).order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = basic_filter

    elif query.task_type == 'month':
        # 本月任务
        month_filter_params.extend(basic_filter_params)
        month_filter = Task.query.filter(*month_filter_params).order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = month_filter
    elif query.task_type == 'week':
        week_filter_params.extend(basic_filter_params)
        week_filter = Task.query.filter(*week_filter_params).order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = week_filter
    elif query.task_type == 'today':
        today_filter_params.extend(basic_filter_params)
        today_filter = Task.query.filter(*today_filter_params).order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = today_filter
    elif query.task_type == 'overtime':
        overtime_filter_params = [
            or_(
                and_(
                    Task.accomplish_time.is_(None),
                    Task.deadline < now
                ),
                Task.deadline < Task.accomplish_time
            )
        ]
        overtime_filter_params.extend(basic_filter_params)
        overtime_filter = Task.query.filter(*overtime_filter_params).order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = overtime_filter
    elif query.task_type == 'not_accomplish':
        not_accomplish_filter_params = [Task.accomplish_time.is_(None)]
        not_accomplish_filter_params.extend(basic_filter_params)
        not_accomplish_filter = Task.query.filter(*not_accomplish_filter_params) \
            .order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = not_accomplish_filter

    page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(filter_param, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get task page error {e}')

    page_dict["today_tasks_count"] = today_tasks_count
    page_dict["week_tasks_count"] = week_tasks_count
    page_dict["month_tasks_count"] = month_tasks_count
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


def handler_private(user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"user is no find")
    return jsonify(
        error_code=RET.OK,
        error_msg="OK",
        data={
            "user_id": user.user_id,
            "user_name": user.user_name
        }
    )
