import json

from flask import g, jsonify, request
from flask_socketio import emit

from server import db, redis_client
from server.model.message import Message
from server.model.group import ReUserGroup, Group
from server.model.user import User
from server.schema.message import MessageModel
from server.schema.group import ReUserGroupSchema, GroupInfoSchema
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.db import collect_sql_error
from server.utils.redis_util import RedisKey


@collect_sql_error
def handler_msg_list():
    # 获取参数
    has_read = int(request.args.get('has_read', 0))
    page_size = int(request.args.get('page_size', 10))
    page_num = int(request.args.get('page_num', 1))
    org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')

    filter_params = [
        Message.to_id == g.user_id,
        Message.is_delete.is_(False),
        Message.org_id == org_id
    ]
    if has_read in [0, 1]:
        filter_params.append(Message.has_read == (True if has_read else False))

    query_filter = Message.query.filter(*filter_params).order_by(Message.create_time.desc(), Message.id.asc())
    page_func = lambda item: MessageModel(**item.to_dict()).dict()
    page_data, e = PageUtil.get_page_dict(query_filter, page_num=page_num, page_size=page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg='OK', data=page_data)


@collect_sql_error
def handler_update_msg():
    msg_id_list = request.json.get('msg_ids')
    is_delete = request.json.get('is_delete')
    has_read = request.json.get('has_read')
    has_all_read = request.json.get('has_all_read')
    org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')

    if not msg_id_list and not has_all_read:
        return jsonify(errro_code=RET.PARMA_ERR, error_msg='msg_ids is not null')
    # 获取数据
    filter_params = [
        Message.to_id == g.user_id,
        Message.is_delete.is_(False),
        Message.org_id == org_id
    ]
    if msg_id_list and not has_all_read:
        filter_params.append(Message.id.in_(msg_id_list))
    update_dict = dict()
    if is_delete:
        update_dict['is_delete'] = is_delete
    if has_read:
        update_dict['has_read'] = has_read
    if not update_dict:
        return jsonify(error_code=RET.PARMA_ERR, error_msg='no params need update')
    Message.query.filter(*filter_params).update(update_dict, synchronize_session=False)
    db.session.commit()
    msg_count = Message.query.filter(Message.to_id == g.user_id,
                                     Message.is_delete.is_(False),
                                     Message.has_read.is_(False),
                                     Message.org_id == org_id).count()
    emit(
        "count",
        {"num": msg_count},
        namespace='/message',
        room=str(g.user_id)
    )
    return jsonify(error_code=RET.OK, error_msg='OK')


@collect_sql_error
def handler_msg_callback(body):
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False).first()
    if not msg:
        raise RuntimeError("the msg does not exist.")
    _data = json.loads(msg.data)
    info = f'<b>您</b>请求{_data.get("_alias")}<b>{_data.get("_id")}</b>已经被{{}}</b>。'
    if body.access:
        info = info.format('管理员处理')
    else:
        info = info.format('管理员拒绝')
    message = Message.create_instance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
    msg.has_read = True

    msg.type = 0
    message.add_update()
    msg.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_addgroup_msg_callback(body):
    org_name = redis_client.hget(RedisKey.user(g.user_id), "current_org_name")
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False, has_read=False).first()
    if not msg:
        raise RuntimeError("the msg does not exist.")
    _data = json.loads(msg.data)
    info = f'您请求加入<b>{org_name}</b>组织下的<b>{_data.get("group_name")}</b>组已经被<b>{{}}</b>。'
    re = ReUserGroup.query.filter_by(
        user_id=msg.from_id,
        group_id=_data.get("group_id"),
        org_id=msg.org_id,
        is_delete=False
    ).first()
    msg.has_read = True
    msg.type = 0
    msg.add_update()
    group = Group.query.filter_by(id=_data.get("group_id"), is_delete=False).first()
    if not group:
        re.delete()
        return jsonify(error_code=RET.OK, error_msg="群组已被解散")
    if not re:
        return jsonify(error_code=RET.OK, error_msg="申请已被其他管理员拒绝")
    if re.role_type != 0:
        return jsonify(error_code=RET.OK, error_msg="申请已被其他管理员处理")
    else:
        if body.access:
            info = info.format('管理员处理')
            re.role_type = 3
            re.user_add_group_flag = 1
            re.add_update()
        else:
            info = info.format('管理员拒绝')
            re.delete()
    message = Message.create_instance(dict(info=info), g.user_id, msg.from_id, msg.org_id)
    message.add_update()

    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_group_page():
    # 从数据库中获取当前用户所有的用户组
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    filter_group = [
        Group.is_delete.is_(False),
        Group.org_id == redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
    ]
    filter_re_user_group = [
        ReUserGroup.user_id == g.user_id,
        ReUserGroup.is_delete.is_(False),
        ReUserGroup.org_id == redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
    ]
    if name:
        filter_group.append(Group.name.like(f"%{name}%"))

    re_user_group_sub = ReUserGroup.query.filter(*filter_re_user_group).subquery()

    query_filter = db.session.query(Group, re_user_group_sub).join(
        re_user_group_sub, Group.id == re_user_group_sub.c.group_id, isouter=True). \
        filter(*filter_group). \
        order_by(
        re_user_group_sub.c.create_time.desc(),
        re_user_group_sub.c.id.asc()
    )

    def page_func(item):
        re_dict = dict()
        re_dict.update({
            "re_user_group_id": item.id,
            "user_add_group_flag": item.user_add_group_flag,
            "re_user_group_is_delete": item.is_delete,
            "re_user_group_role_type": item.role_type,
            "re_user_group_create_time": item.create_time
        })
        group_dict = GroupInfoSchema(**item[0].to_dict()).dict()
        filter_re_user_group = [
            ReUserGroup.is_delete.is_(False),
            ReUserGroup.org_id == redis_client.hget(RedisKey.user(g.user_id), 'current_org_id'),
            ReUserGroup.role_type.in_([1, 2]),
            ReUserGroup.group_id == group_dict.get("id"),
            ReUserGroup.user_add_group_flag.is_(True)
        ]
        group_admin_sub = ReUserGroup.query.filter(*filter_re_user_group).subquery()
        query_res = User.query.join(group_admin_sub, User.user_id == group_admin_sub.c.user_id).all()
        admin_awatar = list()
        for res in query_res:
            admin_awatar.append(dict(user_name=res.user_name, avatar_url=res.avatar_url))
        group_dict.update({
            "admin_awatar": admin_awatar
        })
        return {**re_dict, **group_dict}

    page_dict, e = PageUtil.get_page_dict(query_filter, page_num, page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)
