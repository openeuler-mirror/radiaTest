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

from .routes import (
    VmachineEvent,
    VnicEvent,
    VdiskEvent,
    VmachineControl,
    AttachDevice,
    VmachineEventItem,
    VmachineCallbackEvent,
)


def init_api(api: Api):
    api.add_resource(VmachineEvent, "/api/v1/vmachine")
    api.add_resource(VmachineEventItem, "/api/v1/vmachine/<int:vmachine_id>")
    api.add_resource(VmachineControl, "/api/v1/vmachine/<int:vmachine_id>/power")
    api.add_resource(AttachDevice, "/api/v1/attach")
    api.add_resource(VnicEvent, "/api/v1/vnic")
    api.add_resource(VdiskEvent, "/api/v1/vdisk")
    api.add_resource(VmachineCallbackEvent, "/api/v1/vmachine/callback")
