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

import os
import json

from flask import g
import yaml

from server.model import (
    Message,
    MsgLevel,
    MsgType,
    Role,
    ReUserRole,
)
from server.utils.db import Precise
from server.utils.table_adapter import TableAdapter


class MessageManager:
    @staticmethod
    def get_cur_api_msg(uri, method):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(
            os.path.join(base_dir, "config/api_infos.yaml"), "r", encoding="utf-8"
        ) as f:
            api_infos = yaml.safe_load(f.read())
        uri_arr = uri.split("/")
        url_cnt = len(uri_arr)
        for _api in api_infos:
            _api_arr = _api["uri"].split("/")
            if url_cnt != len(_api_arr):
                continue
            if method.lower() == _api.get("act").lower():
                _is = True
                for i in range(url_cnt):
                    if not uri_arr[i].isdigit() and uri_arr[i] != _api_arr[i]:
                        _is = False
                        break
                if _is:
                    _api["id"] = uri_arr[int(_api.get('index'))] if _api.get('index') else uri_arr[4]
                    _api["cur_uri"] = uri
                    _instance = Precise(
                        getattr(TableAdapter, _api["table"]),
                        {"id": int(_api["id"])},
                    ).first()
                    if _instance.permission_type == "person":
                        return None
                    return _api
        return None

    @staticmethod
    def run(_api):
        from server import redis_client
        from server.utils.redis_util import RedisKey

        _instance = Precise(
            getattr(TableAdapter, _api["table"]),
            {"id": int(_api["id"])},
        ).first()
        if not _instance:
            raise RuntimeError("the data does not exsit")
        cur_org_id = redis_client.hget(RedisKey.user(g.user_id), "current_org_id")
        if _instance.permission_type == "org":
            role = Role.query.filter_by(name="admin", org_id=cur_org_id).first()
        elif _instance.permission_type == "group":
            role = Role.query.filter_by(name="admin", org_id=cur_org_id, group_id=_instance.group_id).first()
        else:
            raise RuntimeError("unknown permission type.")

        if not role:
            raise RuntimeError("the role does not exist.")

        re_role_user = ReUserRole.query.filter_by(role_id=role.id).all()

        if not re_role_user:
            raise RuntimeError("the user with this role does not exist.")

        if hasattr(_instance, "ip"):
            _api.update({
                "ip": _instance.ip
            })
        # 过滤重复触发请求
        request_msgs = Message.query.filter_by(from_id=g.user_id, level=MsgLevel.user.value,
                                               type=MsgType.script.value, is_delete=False, has_read=False).all()
        request_set = set()
        for msg in request_msgs:
            msg_data = json.loads(msg.data)
            url = msg_data.get("callback_url") if msg_data.get("callback_url") else msg_data.get("script")
            if url:
                method = msg_data.get("method", 'none')
                request_set.add(f"{url}_{method}")

        current_unique = f"{_api['cur_uri']}_{_api.get('act', 'none')}"
        if current_unique in request_set:
            # 忽略重复请求
            return f"请勿重复操作，请联系管理员处理未完成的请求"
        info = f'<b>{g.user_login}</b>请求{_api.get("alias")}。'
        if _api.get("ip"):
            info = f'<b>{g.user_login}</b>请求{_api.get("alias")}<b>{_api.get("ip")}</b>。'
        Message.create_instance(json.dumps(
                dict(
                    permission_type=_instance.permission_type,
                    info=info,
                    script=_api["cur_uri"],
                    method=_api.get("act"),
                    _alias=_api.get("alias"),
                    _id=_api.get("id"),
                    body=_api["body"],
                )), g.user_id, [item.user_id for item in re_role_user], cur_org_id,
            level=MsgLevel.user.value, msg_type=MsgType.script.value)
        return "Unauthorized, Your request has been sent to the administrator for processing."
