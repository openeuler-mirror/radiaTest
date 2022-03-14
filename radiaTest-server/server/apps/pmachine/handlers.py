import time
import json

from flask import g, current_app, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from server import redis_client, db
from server.model import Pmachine, IMirroring
from server.model.group import Group, ReUserGroup
from server.utils.response_util import RET
from server.utils.redis_util import RedisKey
from server.utils.db import Edit, Insert, Precise
from server.model.message import Message, MsgType, MsgLevel
from server.utils.shell import ShellCmd
from server.utils.pssh import Connection
from server.utils.bash import (
    pxe_boot,
    power_on_off,
)
from server.utils.pxe import PxeInstall, CheckInstall
from server.utils.response_util import RET


class AutoInstall:
    def __init__(self, body) -> None:
        try:
            self._pmachine = Precise(Pmachine, body).first()
            self._mirroring = Precise(
                IMirroring,
                {
                    "milestone_id": body.get("milestone_id"),
                    "frame": self._pmachine.frame,
                },
            ).first()
        except (IntegrityError, SQLAlchemyError) as e:
            current_app.logger.error(e)
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The selected machine does not exist or the milestone is not bound to the mirror.",
                }
            )

    def kickstart(self):
        if not self._mirroring.efi:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The milestone image does not provide grub.efi path .",
                }
            )

        if not self._pmachine.mac:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The physical machine registration information does not exist in the mac address.",
                }
            )

        if not self._pmachine.ip:
            return jsonify(
                {
                    "error_code": RET.INSTALL_CONF_ERR,
                    "error_msg": "The registration information of the physical machine does not have an IP address.",
                }
            )

        result = PxeInstall(
            self._pmachine.mac, self._pmachine.ip, self._mirroring.efi
        ).bind_efi_mac_ip()
        if isinstance(result, tuple):
            return result

        exitcode, output = ShellCmd(
            pxe_boot(
                self._pmachine.bmc_ip,
                self._pmachine.bmc_user,
                self._pmachine.bmc_password,
            )
        )._exec()
        if exitcode:
            error_msg = (
                "Failed to boot pxe to start the physical machine:%s."
                % self._pmachine.ip
            )
            current_app.logger.error(error_msg)
            current_app.logger.error(output)
            return jsonify({"error_code": RET.INSTALL_CONF_ERR, "error_msg": error_msg})

        result = CheckInstall(self._pmachine.ip).check()
        if isinstance(result, tuple):
            return result

        return jsonify({"error_code": RET.OK, "error_msg": "系统安装成功."})


class OnOff:
    def __init__(self, body) -> None:
        self._body = body

    def on_off(self):
        pmachine = Precise(Pmachine, {"id": self._body.get("id")}).first()
        exitcode, output = ShellCmd(
            power_on_off(
                pmachine.bmc_ip,
                pmachine.bmc_user,
                pmachine.bmc_password,
                self._body.get("status"),
            )
        )._exec()
        if exitcode:
            return jsonify({"error_code": exitcode, "error_msg": output})
        return Edit(Pmachine, self._body).single(Pmachine, '/pmachine')


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