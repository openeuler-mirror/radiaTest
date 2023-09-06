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

from flask import jsonify, g, current_app

from server.utils.db import collect_sql_error
from server.utils.response_util import RET, ssl_cert_verify_error_collect
from server.utils.requests_util import do_request
from server.model import Vmachine, Pmachine
from server.utils.page_util import PageUtil
from server.utils.permission_utils import GetAllByPermission
from server.utils.resource_utils import ResourceManager
from server.utils.auth_util import generate_messenger_token
from server.schema.job import PayLoad


class VmachineHandler:
    @staticmethod
    def get_all(query, workspace=None):
        filter_params = GetAllByPermission(Vmachine, workspace).get_filter()
        p_filter_params = [Pmachine.machine_group_id == query.machine_group_id]
        if query.host_ip:
            p_filter_params.append(Pmachine.ip.like(f"%{query.host_ip}%"))
        pmachines = Pmachine.query.filter(*p_filter_params).all()
        if pmachines:
            pm_ids = [pm.id for pm in pmachines]
            filter_params.append(Vmachine.pmachine_id.in_(pm_ids))
        
        if query.frame:
            filter_params.append(Vmachine.frame == query.frame)
        if query.ip:
            filter_params.append(Vmachine.ip.like(f"%{query.ip}%"))
        if query.name:
            filter_params.append(Vmachine.name.like(f"%{query.name}%"))
        if query.description:
            filter_params.append(
                Vmachine.description.like(f"%{query.description}%")
            )
        
        query_filter = Vmachine.query.filter(*filter_params)

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

    @staticmethod
    @collect_sql_error
    def delete(vmachine_list):
        return ResourceManager("vmachine").del_batch(vmachine_list)


class VmachineMessenger:
    def __init__(self, body):
        self._body = body
        self._body.update({
            "user_id": g.user_id,
        })

    @ssl_cert_verify_error_collect
    def send_request(self, machine_group, api, method, obj=None):
        if obj is None:
            obj = dict()
        payload = PayLoad(g.user_id, g.user_login)
        token = generate_messenger_token(payload)
        _r = do_request(
            method=method,
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
            obj=obj,
            verify=current_app.config.get("CA_CERT"),
        )

        if _r != 0:
            return jsonify(
                error_code=RET.RUNTIME_ERROR,
                error_msg="could not reach messenger of this machine group"
            )

        return jsonify(obj)


class VmachineForceHandler:
    @staticmethod
    @collect_sql_error
    def delete(vmachine_id):
        vmachine = Vmachine.query.filter_by(id=vmachine_id).first()
        if not vmachine:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the vmachine does not exist",
            )

        return ResourceManager("vmachine").del_single(vmachine_id)


def search_device(body, table):
    devices = table.query.filter_by(vmachine_id=body.get("vmachine_id")).all()
    return jsonify({
        "error_code": RET.OK,
        "error_msg": "OK!",
        "data": [data.to_json() for data in devices]
        }
    )
