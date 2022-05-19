import json

from flask import g, jsonify, request
from flask_socketio import emit

from server import db
from server.model.message import Message
from server.schema.message import MessageModel
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.db import collect_sql_error


@collect_sql_error
def handler_msg_list():
    # 获取参数
    has_read = int(request.args.get('has_read', 0))
    page_size = int(request.args.get('page_size', 10))
    page_num = int(request.args.get('page_num', 1))

    filter_params = [
        Message.to_id == g.gitee_id,
        Message.is_delete == False
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
    if not msg_id_list and not has_all_read:
        return jsonify(errro_code=RET.PARMA_ERR, error_msg='msg_ids is not null')
    # 获取数据
    filter_params = [
        Message.to_id == g.gitee_id,
        Message.is_delete == False,
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
    msg_count = Message.query.filter(Message.to_id == g.gitee_id,
                                     Message.is_delete == False,
                                     Message.has_read == False).count()
    emit(
        "count",
        {"num": msg_count},
        namespace='message',
        room=str(g.gitee_id)
    )
    return jsonify(error_code=RET.OK, error_msg='OK')


@collect_sql_error
def handler_msg_callback(body):
    msg = Message.query.filter_by(id=body.msg_id, is_delete=False).first()
    if not msg:
        raise RuntimeError("the msg does not exist.")
    _data = json.loads(msg.data)
    info=f'<b>您</b>请求{_data.get("_alias")}<b>{_data.get("_id")}</b>已经被{{}}</b>。'
    if body.access:
        info = info.format('管理员处理')
    else:
        info = info.format('管理员拒绝')
    message = Message.create_instance(dict(info=info), g.gitee_id, msg.from_id)
    msg.has_read = True

    msg.type = 0
    message.add_update()
    msg.add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")