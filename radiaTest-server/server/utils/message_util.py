import json, yaml, os
from flask import g, jsonify, current_app
from server.utils.response_util import RET

from server.model import (
    ReUserOrganization,
    Message,
    MsgLevel,
    MsgType,
    Role,
    ReUserRole
)
from server.utils.db import Insert, Precise
from server.utils.table_adapter import TableAdapter

class MessageManager:
    @staticmethod
    def get_cur_api_msg(uri, method):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir,'config/api_infos.yaml'), 'r', encoding='utf-8') as f:
            api_infos = yaml.load(f.read(), Loader=yaml.FullLoader)
        
        for _api in api_infos:
            if method == _api.get("act") and _api.get("uri").split("%")[0] in uri:
                uri_s =  _api.get("uri").split("%")
                uri_t1 = uri_s[0]
                uri_t2 = uri_s[1] if len(uri_s) > 1 else ""
                indx = uri.index(uri_t1)
                _api["id"] = uri[indx:].replace(uri_t1, "").replace(uri_t2, "")
                _instance =  Precise(
                    getattr(TableAdapter, _api["table"]), {"id": int(_api["id"])},
                ).first()
                if _instance.permission_type == "person":
                    return None
                return _api
            continue
        return None

    @staticmethod
    def run(_api):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        _instance =  Precise(
            getattr(TableAdapter, _api["table"]), {"id": int(_api["id"])},
        ).first()
        if not _instance:
            raise RuntimeError("the data does not exsit")
        cur_org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        
        re_user_org =  Precise(
            ReUserOrganization, {"gitee_id": _instance.creator_id, "org_id":cur_org_id},
        ).first()
        if not re_user_org:
            current_app.logger.info("the creater user does not exsit in current org")
        
        with open('server/config/role_init.yaml', 'r', encoding='utf-8') as f:
            role_infos = yaml.load(f.read(), Loader=yaml.FullLoader)
        role = Precise(
            Role, {"name": role_infos.get(_instance.permission_type).get("administrator"), "type": _instance.permission_type},
        ).first()

        if not role:
            raise RuntimeError("the role does not exist.")

        re_role_user = Precise(
            ReUserRole, {"role_id": role.id},
        ).first()
        if not re_role_user:
            raise RuntimeError("the user with this role does not exist.")
        MessageManager.send_scrpt_msg(re_role_user.user_id, MsgLevel.user.value, _api, _instance.permission_type)

    @staticmethod
    def send_scrpt_msg(to_user_id, msg_leve: MsgLevel, _api, permission_type):
        from server import redis_client
        from server.utils.redis_util import RedisKey
        _message = dict(
            data=json.dumps(
                dict(
                    permission_type=permission_type,
                    info=f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "gitee_name")}</b>请求{_api.get("alias")}<b>{_api["id"]}</b>。',
                    script=_api.get("uri") % int(_api["id"]), #“/api/v1/product/%d” % instance_id
                    method=_api.get("act"), #"delete"
                    _alias=_api.get("alias"),
                    _id=_api.get("id"),
                    body=_api["body"]
                )
            ),
            level=msg_leve,
            from_id=g.gitee_id,
            to_id=to_user_id,
            type=MsgType.script.value
        )

        Insert(Message, _message).single()
