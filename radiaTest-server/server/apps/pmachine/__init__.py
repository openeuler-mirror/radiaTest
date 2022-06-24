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

from flask_restful import Api

from .routes import PmachineEvent, PmachineItemEvent,PmachineDelayEvent
from .routes import PmachineBmcEvent
from .routes import PmachineSshEvent
from .routes import PmachineOccupyEvent, PmachineReleaseEvent
from .routes import Power
from .routes import Install
from .routes import MachineGroupEvent
from .routes import MachineGroupItemEvent
from .routes import MachineGroupHeartbeatEvent


def init_api(api: Api):
    api.add_resource(PmachineEvent, "/api/v1/pmachine")
    api.add_resource(PmachineItemEvent, "/api/v1/pmachine/<int:pmachine_id>")
    api.add_resource(PmachineBmcEvent, "/api/v1/pmachine/<int:pmachine_id>/bmc")
    api.add_resource(PmachineSshEvent, "/api/v1/pmachine/<int:pmachine_id>/ssh")
    api.add_resource(PmachineOccupyEvent, "/api/v1/pmachine/<int:pmachine_id>/occupy")
    api.add_resource(PmachineReleaseEvent, "/api/v1/pmachine/<int:pmachine_id>/release")
    api.add_resource(PmachineDelayEvent, "/api/v1/pmachine/<int:pmachine_id>/delay")
    api.add_resource(Power, "/api/v1/pmachine/<int:pmachine_id>/power")
    api.add_resource(Install, "/api/v1/pmachine/<int:pmachine>/install")
    api.add_resource(MachineGroupEvent, "/api/v1/machine-group")
    api.add_resource(MachineGroupItemEvent, "/api/v1/machine-group/<int:machine_group_id>")
    api.add_resource(MachineGroupHeartbeatEvent, "/api/v1/machine-group/heartbeat")