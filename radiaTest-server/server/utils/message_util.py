import json, yaml, os
from flask import g, current_app

from server.model import (
    ReUserOrganization,
    Message,
    MsgLevel,
    MsgType,
    Role,
    ReUserRole,
)
from server.utils.db import Insert, Precise
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
        for item in re_role_user:
            MessageManager.send_scrpt_msg(
                item.user_id, MsgLevel.user.value, _api, _instance.permission_type, cur_org_id
            )

    @staticmethod
    def send_scrpt_msg(to_user_id, msg_leve: MsgLevel, _api, permission_type, org_id):
        info = f'<b>{g.user_login}</b>请求{_api.get("alias")}。'
        if _api.get("ip"):
            info = f'<b>{g.user_login}</b>请求{_api.get("alias")}<b>{_api.get("ip")}</b>。'
        _message = dict(
            data=json.dumps(
                dict(
                    permission_type=permission_type,
                    info=info,
                    script=_api["cur_uri"],
                    method=_api.get("act"),
                    _alias=_api.get("alias"),
                    _id=_api.get("id"),
                    body=_api["body"],
                )
            ),
            level=msg_leve,
            from_id=g.user_id,
            to_id=to_user_id,
            type=MsgType.script.value,
            org_id=org_id
        )

        Insert(Message, _message).single()
