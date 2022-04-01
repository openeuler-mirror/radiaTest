import json

from flask import g, current_app, jsonify, request
from sqlalchemy import or_

from server import redis_client
from server.model.pmachine import Pmachine, MachineGroup
from server.model.group import Group, ReUserGroup
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.db import Delete, Edit, Insert, collect_sql_error
from server.model.message import Message, MsgType, MsgLevel
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server.utils.page_util import PageUtil


class ResourcePoolHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = []
        if query.text:
            filter_params.append(
                or_(
                    MachineGroup.name.like(f"%{query.text}%"),
                    MachineGroup.ip.like(f"%{query.text}%")
                )
            )
        
        if query.network_type:
            filter_params.append(
                MachineGroup.network_type == query.network_type
            )
        
        machine_groups = MachineGroup.query.filter(*filter_params).all()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[machine_group.to_json() for machine_group in machine_groups]
        )
        
    @staticmethod
    @collect_sql_error
    def get(machine_group_id):
        machine_group = MachineGroup.query.filter_by(
            id=machine_group_id
        ).first()
        if not machine_group:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                errror_msg="the machine group does not exist"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=machine_group.to_json()
        )

    @staticmethod
    @collect_sql_error
    def create_group(body):
        return Insert(MachineGroup, body.__dict__).single(
            MachineGroup, 
            "/machine_group"
        )

    @staticmethod
    @collect_sql_error
    def update_group(machine_group_id, body):
        _body = body.__dict__
        _body.udpate({"id": machine_group_id})
        return Edit(MachineGroup, _body).single(MachineGroup, "/machine_group")

    @staticmethod
    @collect_sql_error
    def delete_group(machine_group_id):
        return Delete(MachineGroup, {"id": machine_group_id}).single(
            MachineGroup, 
            "/machine_group"
        )


class PmachineHandler:
    @staticmethod
    def get_all(query):
        filter_params = [
            Pmachine.machine_group_id == query.machine_group_id
        ]

        if query.mac:
            filter_params.append(Pmachine.mac.like(f"%{query.mac}%"))
        if query.frame:
            filter_params.append(Pmachine.frame == query.frame)
        if query.ip:
            filter_params.append(Pmachine.ip.like(f"%{query.ip}%"))
        if query.bmc_ip:
            filter_params.append(Pmachine.bmc_ip.like(f"%{query.bmc_ip}%"))
        if query.occupier:
            filter_params.append(Pmachine.occupier.like(f"%{query.occupier}%"))
        if query.description:
            filter_params.append(
                Pmachine.description.like(f"%{query.description}%")
            )
        
        if query.state:
            filter_params.append(Pmachine.state == query.state)
        
        query_filter = Pmachine.query.filter(*filter_params)

        def page_func(item):
            return item.to_json()

        page_dict, e = PageUtil.get_page_dict(
            query_filter, 
            query.page_num, 
            query.page_size, 
            func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR, 
                error_msg=f'get group page error {e}'
            )
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


class PmachineMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": int(g.gitee_id),
        })

    def send_request(self, machine_group, api):
        _resp = dict()
        _r = do_request(
            method="put",
            url="{}://{}:{}{}".format(
                current_app.config.get("PROTOCOL"),
                machine_group.ip,
                machine_group.listen,
                api
            ),
            body=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": request.headers.get("authorization")
            },
            obj=_resp
        )

        if _r !=0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(_resp)


class StateHandler:
    english_to_chinese = {
        "release": "释放",
        "occupied": "占用"
    }

    def __init__(self, machine_id, to_state):
        self.pmachine = Pmachine.query.filter_by(id=machine_id).first()
        self.to_state = to_state    
    
    def change_state(self):
        if not self.pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR, 
                error_msg="The pmachine is not exist"
            )
        
        if self.pmachine.state == self.to_state:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The pamachine has been {}".format(self.to_state)
            )
        
        # 暂时请求通知统一发送于openEuler-QA的创建者
        org_id = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        filter_params = [
            Group.name == current_app.config.get("OE_QA_GROUP_NAME"),
            Group.is_delete == False,
            ReUserGroup.is_delete == False,
            ReUserGroup.org_id == org_id,
            ReUserGroup.role_type == 1,
        ]
        re = ReUserGroup.query.join(Group).filter(*filter_params).first() 

        if not re:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="The group which machine belongs to is not exist")

        _message = dict(
            data=json.dumps(
                dict(
                    group_id=re.group.id,
                    info=f'<b>{redis_client.hget(RedisKey.user(g.gitee_id), "gitee_name")}</b>请求{StateHandler.english_to_chinese.get(self.to_state)}物理机<b>{self.pmachine.ip}</b>。'
                )
            ),
            level=MsgLevel.user.value,
            from_id=g.gitee_id,
            to_id=re.user.gitee_name,
            type=MsgType.script.value
        )

        return Insert(Message, _message).single()