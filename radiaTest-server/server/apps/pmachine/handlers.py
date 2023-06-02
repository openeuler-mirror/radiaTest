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
import datetime
import pytz

from flask import g, current_app, jsonify
from sqlalchemy import or_
import sqlalchemy

from server import redis_client
from server.model.pmachine import Pmachine, MachineGroup
from server.model.group import Group, ReUserGroup
from server.model.message import Message, MsgType, MsgLevel
from server.model.permission import Scope, Role, ReScopeRole
from server.utils.response_util import ssl_cert_verify_error_collect
from server.utils.redis_util import RedisKey
from server.utils.db import Insert, Edit, collect_sql_error, Delete
from server.utils.requests_util import do_request
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server.utils.auth_util import generate_messenger_token
from server.schema.job import PayLoad
from server.model.user import User
from server.utils.mail_util import Mail
from server.model.vmachine import Vmachine


class ResourcePoolHandler:     
    @staticmethod
    @collect_sql_error
    def get_all(query, workspace=None):
        filter_params = GetAllByPermission(MachineGroup, workspace).get_filter()

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
            data=[machine_group.to_json()]
        )

    @staticmethod
    @collect_sql_error
    def delete_group(machine_group_id):
        return ResourceManager("machine_group").del_cascade_single(
            machine_group_id,
            Pmachine,
            [
                Pmachine.machine_group_id == machine_group_id
            ],
            False
            )


class PmachineHandler:
    @staticmethod
    def get_all(query, workspace=None):
        filter_params = GetAllByPermission(Pmachine, workspace).get_filter()
        filter_params.append(Pmachine.machine_group_id == query.machine_group_id)

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
            return item.to_public_json()

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


class PmachineOccupyReleaseHandler:
    def __init__(self):
        self.scopes_list = ['occupy', 'release', 'power', 'install', 'ssh', 'data']

    @staticmethod
    def check_scope_exist(act, uri, eft):
        scope = Scope.query.filter_by(act=act, uri=uri, eft=eft).first()
        if not scope:
            return False, None
        return True, scope

    def occupy_with_bind_scopes(self, pmachine_id, body):
        pmachine = Pmachine.query.filter_by(id=pmachine_id).first()
        if not pmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="The pmachine does not exist. Please check."
            )
        if pmachine.state == "occupied":
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Pmachine state has not been modified. Please check."
            )

        if not all((pmachine.ip, pmachine.user, pmachine.password, pmachine.port,)):
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="The pmachine lacks of SSH info. Please add."
            )

        # 若当前请求用户非创建者，则进行临时赋权
        if body.occupier_id != pmachine.creator_id:
            role = Role.query.filter_by(type='person', name=body.occupier_id).first()
            if not role:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The role policy info is invalid."
                )

            for sub_uri in self.scopes_list:
                _uri = '/api/v1/pmachine/{}'.format(pmachine.id)
                if sub_uri != 'data':
                    _uri += f'/{sub_uri}'
                
                exist, scope = PmachineOccupyReleaseHandler.check_scope_exist(
                    act='put',
                    uri=_uri,
                    eft='allow'
                )
                if not exist:
                    return jsonify(
                        error_code=RET.NO_DATA_ERR,
                        error_msg=f"policy put_{_uri}_allow does not exist"
                    )
                
                bind_body = {
                    "role_id": role.id,
                    "scope_id": scope.id,
                }
                Insert(ReScopeRole, bind_body).single()
            
        _body = body.__dict__
        end_time = _body.get("end_time")
        if end_time:
            _body.update({
                "end_time": datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").
                    astimezone(pytz.timezone('Asia/Shanghai'))
            })
        _body.update({
            "id": pmachine_id,
            "state": "occupied"
        })

        return Edit(Pmachine, _body).single(Pmachine, "/pmachine")

    def release_with_release_scopes(self, pmachine):
        if pmachine.state == "idle":
            return jsonify(
                error_code=RET.VERIFY_ERR,
                error_msg="Pmachine state has not been modified. Please check."
            )
        if pmachine.state == "occupied" and pmachine.description \
                == current_app.config.get("CI_HOST"):
            vmachine = Vmachine.query.filter_by(pmachine_id=pmachine.id).first()
            if vmachine:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="Pmachine has vmmachine, can't released."
                )

        # 修改随机密码
        _body = {
            "id": pmachine.id,
            "ip": pmachine.ip,
            "user": pmachine.user,
            "port": pmachine.port,
            "old_password": pmachine.password,
            "random_flag": True,
        }

        if pmachine.description in [current_app.config.get("CI_HOST"),
                                    current_app.config.get("CI_PURPOSE")]:
            _body.update(
                {
                    "random_flag": False
                }
            )

        if _body.get("random_flag"):
            _resp = PmachineMessenger(_body).send_request(
                pmachine.machine_group,
                "/api/v1/pmachine/ssh",
            )

            _resp = json.loads(_resp.data.decode('UTF-8'))
            if _resp.get("error_code") != RET.OK:
                current_app.logger.error(
                    f"release pmachine {pmachine.id} failed, "
                    f"messenger return {_resp} when resetting password"
                )
                return jsonify(
                    error_code=RET.BAD_REQ_ERR,
                    error_msg="Modify ssh password error, can't released."
                )
            else:
                messenger_res = _resp.get("error_msg")
                current_app.logger.info("messenger response info:{}".format(messenger_res))
                pmachine_passwd = _resp.get("data")
                if isinstance(pmachine_passwd, list):
                    mail = Mail()
                    mail.send_text_mail(
                        current_app.config.get("ADMIN_MAIL_ADDR"),
                        subject="【radiaTest平台】{}-密码变更通知".format(pmachine_passwd[0]),
                        text="{} new password:{}".format(pmachine_passwd[0], pmachine_passwd[1])
                    )
                else:
                    return jsonify(
                        error_code=RET.BAD_REQ_ERR,
                        error_msg="messenger response is not correct"
                    )
        if pmachine.state == "occupied":
            _body = {
                "description": sqlalchemy.null(),
                "occupier": sqlalchemy.null(),
                "occupier_id": sqlalchemy.null(),
                "start_time": sqlalchemy.null(),
                "end_time": sqlalchemy.null(),
                "state": "idle",
                "listen": sqlalchemy.null(),
            }

        resp = Edit(Pmachine, _body).single(Pmachine, "/pmachine")
        _resp = json.loads(resp.response[0])
        if _resp.get("error_code") != RET.OK:
            return _resp

            # 删除权利
        if pmachine.occupier_id != pmachine.creator_id:
            role = Role.query.filter_by(type='person', name=pmachine.occupier_id).first()
            if not role:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="The role policy info is invalid."
                )

            for sub_uri in self.scopes_list:
                _uri = '/api/v1/pmachine/{}'.format(pmachine.id)
                if sub_uri != 'data':
                    _uri += f'/{sub_uri}'

                exist, scope = PmachineOccupyReleaseHandler.check_scope_exist(
                    act='put',
                    uri=_uri,
                    eft='allow'
                )
                if not exist:
                    continue

                re_scope_role = ReScopeRole.query.filter_by(scope_id=scope.id, role_id=role.id).all()

                for item in re_scope_role:
                    Delete(ReScopeRole, {"id": item.id}).single()

        return jsonify(error_code=RET.OK, error_msg="OK")


class PmachineMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": g.user_id,
        })

    @ssl_cert_verify_error_collect
    def send_request(self, machine_group, api):
        _resp = dict()
        payload = PayLoad(g.user_id, g.user_login)
        token = generate_messenger_token(payload)
        _r = do_request(
            method="put",
            url="https://{}:{}{}".format(
                machine_group.messenger_ip,
                machine_group.messenger_listen,
                api
            ),
            body=self._body,
            headers={
                "content-type": "application/json;charset=utf-8",
                "authorization": f"JWT {token}"
            },
            obj=_resp,
            verify=current_app.config.get("CA_CERT"),
        )

        if _r != 0:
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
        org_id = redis_client.hget(RedisKey.user(g.user_id), 'current_org_id')
        filter_params = [
            Group.name == current_app.config.get("OE_QA_GROUP_NAME"),
            Group.is_delete.is_(False),
            ReUserGroup.is_delete.is_(False),
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
                    info=f'<b>{redis_client.hget(RedisKey.user(g.user_id), "user_name")}</b>\
                    请求{StateHandler.english_to_chinese.get(self.to_state)}物理机<b>{self.pmachine.ip}</b>。'
                )
            ),
            level=MsgLevel.user.value,
            from_id=g.user_id,
            to_id=re.user.user_name,
            type=MsgType.script.value,
            org_id=org_id
        )

        return Insert(Message, _message).single()
