import json, yaml, os
from flask import g, jsonify, current_app
from server.utils.response_util import RET

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
            api_infos = yaml.load(f.read(), Loader=yaml.FullLoader)
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
                    _api["id"] = uri_arr[4]
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
        cur_org_id = redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")

        re_user_org = Precise(
            ReUserOrganization,
            {"gitee_id": _instance.creator_id, "org_id": cur_org_id},
        ).first()
        if not re_user_org:
            current_app.logger.info("the creater user does not exsit in current org")

        with open("server/config/role_init.yaml", "r", encoding="utf-8") as f:
            role_infos = yaml.load(f.read(), Loader=yaml.FullLoader)
        role = Precise(
            Role,
            {
                "name": role_infos.get(_instance.permission_type).get("administrator"),
                "type": _instance.permission_type,
            },
        ).first()

        if not role:
            raise RuntimeError("the role does not exist.")

        re_role_user = Precise(
            ReUserRole,
            {"role_id": role.id},
        ).first()
        if not re_role_user:
            raise RuntimeError("the user with this role does not exist.")
        MessageManager.send_scrpt_msg(
            re_role_user.user_id, MsgLevel.user.value, _api, _instance.permission_type
        )

    @staticmethod
    def send_scrpt_msg(to_user_id, msg_leve: MsgLevel, _api, permission_type):
        from server import redis_client
        from server.utils.redis_util import RedisKey

        _message = dict(
            data=json.dumps(
                dict(
                    permission_type=permission_type,
                    info=f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "gitee_name")}</b>请求{_api.get("alias")}<b>{_api["id"]}</b>。',
                    script=_api["cur_uri"],
                    method=_api.get("act"),
                    _alias=_api.get("alias"),
                    _id=_api.get("id"),
                    body=_api["body"],
                )
            ),
            level=msg_leve,
            from_id=g.gitee_id,
            to_id=to_user_id,
            type=MsgType.script.value,
        )

        Insert(Message, _message).single()
