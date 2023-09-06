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
import sqlalchemy

from server import redis_client
from server.utils.response_util import RET
from server.utils.oauth_util import LoginApi
from server.utils.auth_util import generate_token
from server.utils.redis_util import RedisKey
from server.utils.db import collect_sql_error, Insert
from server.utils.cla_util import Cla, ClaShowAdminSchema
from server.utils.read_from_yaml import get_default_suffix
from server.utils.page_util import PageUtil
from server.model.user import User
from server.model.message import Message
from server.model.task import Task
from server.model.vmachine import Vmachine
from server.model.pmachine import Pmachine
from server.model.milestone import Milestone
from server.model.organization import Organization, ReUserOrganization
from server.model.group import ReUserGroup, GroupRole
from server.model.testcase import Commit
from server.model.permission import Role, ReUserRole
from server.schema.group import ReUserGroupSchema, GroupInfoSchema
from server.schema.organization import OrgUserInfoSchema, ReUserOrgSchema
from server.schema.user import UserInfoSchema, UserTaskSchema, UserMachineSchema, UserCaseCommitSchema
from server.schema.task import TaskInfoSchema
from server.schema.vmachine import VmachineBriefSchema
from server.schema.pmachine import PmachineBriefSchema
from server.utils.page_util import PageUtil
from server.utils.requests_util import do_request
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
        org.oauth_login_url,
        org.oauth_client_id,
        current_app.config.get("OAUTH_REDIRECT_URI"),
        deal_scope(org.oauth_scope)
    )
    return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=oauth_login_url
        )


def send_majun(code):
    _resp = dict()
    
    majun_api = current_app.config.get("MAJUN_API")
    access_token = current_app.config.get("MAJUN_ACCESS_TOKEN")
    _r = do_request(
        method="get",
        url="https://{}?code={}".format(
            majun_api,
            code,
        ),
        headers={
            "content-type": "application/json;charset=utf-8",
            "authorization": request.headers.get("authorization"),
            "access_token": access_token,
        },
        obj=_resp,
        verify=True,
    )
    if _r != 0:
        return jsonify(
            error_code=RET.RUNTIME_ERROR,
            error_msg="could not reach majun system."
        )
    return jsonify(_resp)


def handler_oauth_callback():
    # 校验参数
    code = request.args.get('code')
    if not code:
        return jsonify(
            error_code=RET.PARMA_ERR,
            error_msg="user code should not be null"
        )
    cookie_info = request.cookies.to_dict()
    if "user_id" in cookie_info:
        resp = send_majun(code)
        _resp = json.loads(resp.response[0])
        current_app.logger.info(_resp)

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
        org.oauth_get_token_url,
        query.code,
        org.oauth_client_id,
        current_app.config.get("OAUTH_REDIRECT_URI"),
        org.oauth_client_secret
    )
        
    if not oauth_flag:
        return jsonify(
            error_code=RET.OTHER_REQ_ERR,
            error_msg="oauth request error"
        )

    result = handler_login(oauth_token, org.id, org.oauth_get_user_info_url, org.authority)
    if not isinstance(result, tuple) or not isinstance(result[0], bool):
        return result
    if result[0]:
        resp = Response(content_type="application/json")
        resp.set_data(
            json.dumps(
                {
                    "error_code": RET.OK,
                    "error_msg": "OK",
                    "data": {
                        "url": f'{current_app.config["OAUTH_HOME_URL"]}?isSuccess=True',
                        "user_id": result[1],
                        "token": result[2]
                    }
                }
            )
        )
        resp.status = 200
        return resp
    else:
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data={
                "url": '{}?isSuccess=False&user_id={}&org_id={}&require_cla={}'.format(
                current_app.config["OAUTH_HOME_URL"],
                result[1],
                org.id,
                org.cla_verify_url is not None
                )
            }
        )


@collect_sql_error
def handler_login(oauth_token, org_id, oauth_user_info_url, authority):
    """
    处理用户登录
    :param oauth_token: oauth_token
    :param org_id: 当前登入的组织id
    :param oauth_user_info_url: 鉴权机构的获取用户信息url
    :param authority: 鉴权机构
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
    # 先将token缓存到redis中, 有效期为10min，这段时间主要用来是验证cla签名
    profile["access_token"] = oauth_token.get("access_token")
    profile["refresh_token"] = oauth_token.get("refresh_token")
    redis_client.hmset(
        RedisKey.oauth_user(profile.get("user_id")),
        profile,
        ex=60 * 60 * 2,
    )

    # 从数据库中获取用户信息
    user = User.query.filter_by(user_id=profile.get("user_id")).first()
    # 判断用户是否存在
    if user:
        user = User.synchronize_oauth_info(profile, user)

        # 生成token值
        token = generate_token(
            user.user_id,
            user.user_login,
            int(current_app.config.get("LOGIN_EXPIRES_TIME"))
        )

        if org_id is not None and isinstance(org_id, int):
            re = ReUserOrganization.query.filter_by(
                user_id=profile.get("user_id"),
                organization_id=org_id,
                is_delete=False,
            ).first()
            if not re:
                return False, profile.get("user_id")

            redis_client.hset(
                RedisKey.user(profile.get("user_id")),
                'current_org_id',
                org_id
            )
            redis_client.hset(
                RedisKey.user(profile.get("user_id")),
                'current_org_name',
                re.organization.name
            )

            if re.default is False:
                _resp = handler_select_default_org(org_id, profile.get("user_id"))
                _r = None
                try:
                    _r = _resp.json
                except (AttributeError, TypeError) as e:
                    raise RuntimeError(str(e)) from e
                if _r.get("error_code") != RET.OK:
                    return False, profile.get("user_id")

        return True, user.user_id, token

    # 返回结果
    return False, profile.get("user_id")


@collect_sql_error
def handler_register(user_id, body):
    # 从redis中获取之前的用户信息
    oauth_user = redis_client.hgetall(RedisKey.oauth_user(user_id))
    if not oauth_user:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg="user info expired"
        )

    # 从数据库中获取cla信息
    org = Organization.query.filter_by(
        id=body.organization_id,
        is_delete=False
    ).first()
    if not org:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg=f"the organization does not exist"
        )

    # 若组织需要CLA签署验证，则判断是否已签署CLA
    if org.cla_verify_url and not Cla.is_cla_signed(
            ClaShowAdminSchema(**org.to_dict()).dict(),
            body.cla_verify_params,
            body.cla_verify_body
    ):
        return jsonify(
            error_code=RET.CLA_VERIFY_ERR,
            error_msg="user is not pass cla verification, please retry",
            data=oauth_user.get("user_id")
        )

    # 提取cla邮箱
    cla_email = None
    for key, value in {
        **body.cla_verify_params,
        **body.cla_verify_body
    }.items():
        if 'email' in key:
            cla_email = value
            break

    user = User.query.filter_by(user_id=oauth_user.get("user_id")).first()
    if not user:
        # 用户注册成功保存用户信息、生成token
        user = User.create_commit(
            oauth_user,
            cla_email,
        )

    # 查询用户和组织是否已存在关系
    re = ReUserOrganization.query.filter_by(
        is_delete=False,
        user_id=user.user_id,
        organization_id=org.id,
    ).first()
    if not re:
        # 生成用户和组织的关系
        _ = ReUserOrganization.create(
            user.user_id,
            org.id,
            json.dumps({
                **body.cla_verify_params,
                **body.cla_verify_body
            }),
            default=False
        )
    
    _role = Role.query.filter_by(name=user.user_id, type='person').first()
    if not _role:
        role = Role(name=user.user_id, type='person')
        role_id = role.add_flush_commit_id()
        Insert(ReUserRole, {"user_id": user.user_id, "role_id": role_id}).single()

    # 绑定用户和组织基础角色、公共基础角色的关系
    org_suffix = get_default_suffix('org')
    public_suffix = get_default_suffix('public')
    filter_params = [
        or_(
            and_(
                Role.org_id == org.id,
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
        Insert(ReUserRole, {"user_id": user.user_id, "role_id": _role.id}).single()

    # 用户缓存到redis中
    redis_client.hset(
        RedisKey.user(oauth_user.get("user_id")),
        'current_org_name',
        org.name
    )

    # 生成token值
    token = generate_token(
        user.user_id,
        user.user_login,
        int(current_app.config.get("LOGIN_EXPIRES_TIME"))
    )
    return_data = {
        'token': token,
    }

    # 将当前组织设为注册组织
    _resp = handler_select_default_org(org.id, oauth_user.get("user_id"))
    _r = None
    try:
        _r = _resp.json
    except (AttributeError, RuntimeError) as e:
        return jsonify(
            error_code=RET.SERVER_ERR,
            error_msg=f"SERVER ERROR: {str(e)}"
        )
    if _r.get("error_code") != RET.OK:
        raise RuntimeError(_r.get("error_msg"))

    return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)


@collect_sql_error
def handler_update_user(user_id, body):
    if g.user_id != user_id:
        return jsonify(
            error_code=RET.VERIFY_ERR,
            error_msg="user token and user id do not match"
        )

    # 从数据库中获取用户信息
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"user is no find")

    # 修改数据保存到数据库
    user.phone = body.phone
    user.add_update()
    # 修改缓存中的数据
    redis_client.hset(RedisKey.user(user_id), 'phone', body.phone)
    return jsonify(error_code=RET.OK, error_msg="OK")


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
    orgs = user.re_user_organization
    if orgs:
        for item in orgs:
            re_user_organization = ReUserOrgSchema(**item.to_dict())
            org = OrgUserInfoSchema(**item.organization.to_dict())
            if not org.is_delete:
                org_list.append({**re_user_organization.dict(), **org.dict()})
    user_dict["orgs"] = org_list
    user_dict = UserInfoSchema(**user_dict).dict()
    return jsonify(error_code=RET.OK, error_msg="OK", data=user_dict)


def handler_logout():
    redis_client.delete(RedisKey.user(g.user_id))
    redis_client.delete(RedisKey.token(g.user_id))
    redis_client.delete(RedisKey.token(g.token))
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_select_default_org(org_id, user_id=None):
    if user_id is None:
        user_oauth_id = g.user_id
    else:
        user_oauth_id = user_id

    re = ReUserOrganization.query.filter_by(
        user_id=user_oauth_id,
        organization_id=org_id,
        is_delete=False
    ).first()

    if not re:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg="relationship no find"
        )

    # 切换数据
    re_old = ReUserOrganization.query.filter_by(
        user_id=user_oauth_id,
        default=True,
        is_delete=False
    ).first()

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
    redis_client.hset(
        RedisKey.user(user_oauth_id),
        'current_org_id',
        org_id
    )
    redis_client.hset(
        RedisKey.user(user_oauth_id),
        'current_org_name',
        re.organization.name
    )
    return jsonify(error_code=RET.OK, error_msg="OK")


def handler_add_group(group_id, body):
    re = ReUserGroup.query.filter_by(user_id=g.user_id, group_id=group_id, is_delete=False).first()
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False).first()
    if not re or not msg:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="relationship no find")
    if re.user_add_group_flag or re.role_type == GroupRole.user.value:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="relationship is exist")
    info = f'<b>{re.user.user_name}</b>{{}}' \
           f'<b>{redis_client.hget(RedisKey.user(g.user_id), "current_org_name")}' \
           f'</b>组织下<b>{re.group.name}</b>用户组'
    if body.access:
        re.user_add_group_flag = True
        re.role_type = GroupRole.user.value
        info = info.format('已加入')
        message = Message.create_instance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
        message1 = Message.create_instance(dict(info=info), g.user_id, g.user_id, msg.org_id)

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
        message = Message.create_instance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
        message1 = Message.create_instance(dict(info=info), g.user_id, g.user_id, msg.org_id)
    msg.is_delete = True
    re.add_update()
    message.add_update()
    message1.add_update()
    msg.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_get_all(query):
    filter_params = []

    if query.user_id:
        filter_params.append(User.user_id.like(f'%{query.user_id}%'))
    if query.user_login:
        filter_params.append(User.user_id.like(f'%{query.user_login}%'))
    if query.user_name:
        filter_params.append(User.user_id.like(f'%{query.user_name}%'))

    query_filter = User.query.filter(*filter_params).order_by(User.create_time.desc(), User.user_id.asc())

    # 获取用户组下的所有用户
    def page_func(item):
        user_dict = item.to_json()
        return user_dict

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
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
    basic_filter_params = [Task.is_delete.is_(False),
                           Task.executor_id == g.user_id,
                           Task.org_id == current_org_id]

    # 今日任务总数
    today_filter_params = [extract('year', Task.create_time) == now.year,
                           extract('month', Task.create_time) == now.month,
                           extract('day', Task.create_time) == now.day]
    today_filter_params.extend(basic_filter_params)
    today_tasks_count = Task.query.filter(*today_filter_params).count()

    # 本周任务总数
    today = datetime(now.year, now.month, now.day, 0, 0, 0)
    this_week_start = today - timedelta(days=now.weekday())
    this_week_end = today + timedelta(days=7 - now.weekday())
    week_filter_params = [Task.create_time >= this_week_start,
                          Task.create_time < this_week_end]
    week_filter_params.extend(basic_filter_params)
    week_tasks_count = Task.query.filter(*week_filter_params).count()

    # 本月任务总数
    this_month_start = datetime(now.year, now.month, 1)
    if now.month < 12:
        next_month_start = datetime(now.year, now.month + 1, 1)
    else:
        next_month_start = datetime(now.year+1, 1, 1)
    
    month_filter_params = [Task.create_time >= this_month_start,
                           Task.create_time < next_month_start]
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
        not_accomplish_filter = Task.query.filter(*not_accomplish_filter_params)\
            .order_by(Task.update_time.desc(), Task.id.asc())
        filter_param = not_accomplish_filter

    page_dict, e = PageUtil.get_page_dict(filter_param, query.page_num, query.page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get task page error {e}')

    page_dict["today_tasks_count"] = today_tasks_count
    page_dict["week_tasks_count"] = week_tasks_count
    page_dict["month_tasks_count"] = month_tasks_count
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_get_user_machine(query: UserMachineSchema):
    current_org_id = int(redis_client.hget(
        RedisKey.user(g.user_id),
        'current_org_id'
    ))
    page_dict = None
    if query.machine_type == 'physics':
        def page_func(item: Pmachine):
            item_dict = PmachineBriefSchema(**item.__dict__).dict()
            return item_dict

        filter_params = [
            or_(
                Pmachine.occupier == User.query.get(g.user_id).user_name,
                Pmachine.creator_id == g.user_id,
            ),
            Pmachine.org_id == current_org_id
        ]
        if query.machine_name:
            filter_params.append(or_(
                Pmachine.ip.like(f'%{query.machine_name}%'),
                Pmachine.description.like(f'%{query.machine_name}%'),
                Pmachine.bmc_ip.like(f'%{query.machine_name}%')
            ))
        filter_chain = Pmachine.query.filter(*filter_params).order_by(Pmachine.create_time.desc(), Pmachine.id.asc())
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get pmachine page error {e}')
    elif query.machine_type == 'virtual':
        def page_func(item: Vmachine):
            item_dict = VmachineBriefSchema(**item.__dict__).dict()
            return item_dict

        filter_params = [
            Vmachine.creator_id == g.user_id,
            Vmachine.org_id == current_org_id
        ]
        if query.machine_name:
            filter_params.append(or_(
                Vmachine.ip.like(f'%{query.machine_name}%'),
                Vmachine.description.like(f'%{query.machine_name}%'),
                Vmachine.milestone.like(f'%{query.machine_name}%')
            ))
        filter_chain = Vmachine.query.filter(*filter_params).order_by(Vmachine.create_time.desc(), Vmachine.id.asc())
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get vmachine page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_get_user_case_commit(query: UserCaseCommitSchema):
    current_org_id = int(redis_client.hget(
        RedisKey.user(g.user_id),
        'current_org_id'
    ))
    now = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
    # 全部
    basic_filter_params = [
        Commit.creator_id == g.user_id,
        Commit.status == 'accepted',
        Commit.org_id == current_org_id
    ]

    # 今日贡献
    today_filter_params = [extract('year', Commit.create_time) == now.year,
                           extract('month', Commit.create_time) == now.month,
                           extract('day', Commit.create_time) == now.day]
    today_filter_params.extend(basic_filter_params)
    today_count = Commit.query.filter(*today_filter_params).count()

    # 本周贡献
    today = datetime(now.year, now.month, now.day, 0, 0, 0)
    this_week_start = today - timedelta(days=now.weekday())
    this_week_end = today + timedelta(days=7 - now.weekday())
    week_filter_params = [Commit.create_time >= this_week_start,
                          Commit.create_time < this_week_end]
    week_filter_params.extend(basic_filter_params)
    week_count = Commit.query.filter(*week_filter_params).count()

    # 本月贡献
    this_month_start = datetime(now.year, now.month, 1)
    if now.month < 12:
        next_month_start = datetime(now.year, now.month + 1, 1)
    else:
        next_month_start = datetime(now.year+1, 1, 1)

    month_filter_params = [Commit.create_time >= this_month_start,
                           Commit.create_time < next_month_start]
    month_filter_params.extend(basic_filter_params)
    month_count = Commit.query.filter(*month_filter_params).count()

    filter_params = [Commit.creator_id == g.user_id]
    if query.title:
        filter_params.append(Commit.title.like(f'%{query.title}%'))

    if query.status != 'all':
        filter_params.append(Commit.status == query.status)
    else:
        filter_params.append(Commit.status != 'pending')
    filter_chain = Commit.query.filter(*filter_params).order_by(Commit.create_time.desc(), Commit.id.asc())
    page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get case commit page error {e}')

    page_dict["today_case_count"] = today_count
    page_dict["week_case_count"] = week_count
    page_dict["month_case_count"] = month_count
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_get_user_case_commit(query: UserCaseCommitSchema):
    now = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
    # 全部
    basic_filter_params = [Commit.creator_id == g.user_id, Commit.status == 'accepted']

    # 今日贡献
    today_filter_params = [extract('year', Commit.create_time) == now.year,
                           extract('month', Commit.create_time) == now.month,
                           extract('day', Commit.create_time) == now.day]
    today_filter_params.extend(basic_filter_params)
    today_count = Commit.query.filter(*today_filter_params).count()

    # 本周贡献
    today = datetime(now.year, now.month, now.day, 0, 0, 0)
    this_week_start = today - timedelta(days=now.weekday())
    this_week_end = today + timedelta(days=7 - now.weekday())
    week_filter_params = [Commit.create_time >= this_week_start,
                          Commit.create_time < this_week_end]
    week_filter_params.extend(basic_filter_params)
    week_count = Commit.query.filter(*week_filter_params).count()

    # 本月贡献
    this_month_start = datetime(now.year, now.month, 1)
    if now.month < 12:
        next_month_start = datetime(now.year, now.month + 1, 1)
    else:
        next_month_start = datetime(now.year+1, 1, 1)
    
    month_filter_params = [Commit.create_time >= this_month_start,
                           Commit.create_time < next_month_start]
    month_filter_params.extend(basic_filter_params)
    month_count = Commit.query.filter(*month_filter_params).count()

    filter_params = [Commit.creator_id == g.user_id]
    if query.title:
        filter_params.append(Commit.title.like(f'%{query.title}%'))

    if query.status != 'all':
        filter_params.append(Commit.status == query.status)
    else:
        filter_params.append(Commit.status != 'pending')
    filter_chain = Commit.query.filter(*filter_params).order_by(Commit.create_time.desc(), Commit.id.asc())
    page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get case commit page error {e}')

    page_dict["today_case_count"] = today_count
    page_dict["week_case_count"] = week_count
    page_dict["month_case_count"] = month_count
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


def handler_get_user_asset_rank(query):
    ranked_user = User.query.join(
        ReUserOrganization
    ).filter(
        ReUserOrganization.rank != sqlalchemy.null(),
        ReUserOrganization.is_delete == False,
        ReUserOrganization.organization_id == redis_client.hget(
            RedisKey.user(g.user_id), 
            "current_org_id"
        )
    ).order_by(
        ReUserOrganization.rank.asc(), 
        User.create_time.asc()
    )

    def page_func(item):
        user_dict = item.to_summary()
        return user_dict
    
    page_dict, e = PageUtil.get_page_dict(
        ranked_user, query.page_num, query.page_size, func=page_func
    )
    if e:
        return jsonify(
            error_code=RET.SERVER_ERR, 
            error_msg=f'get user rank page error {e}'
        )
    return jsonify(
        error_code=RET.OK, 
        error_msg="OK", 
        data=page_dict
    )

    
