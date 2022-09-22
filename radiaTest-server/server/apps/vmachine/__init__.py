# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/20
# @License : Mulan PSL v2
#####################################

from flask_restful import Api

from .routes import (
    VmachineEvent,
    VnicEvent,
    VdiskEvent,
    VmachineControl,
    AttachDevice,
    VmachineItemEvent,
    VmachineDelayEvent,
    VmachineBatchDelayEvent,
    VmachineItemForceEvent,
    VmachineData,
    VmachineItemData,
    VnicData,
    VnicItemData,
    VdiskData,
    VdiskItemData,
    PreciseVmachineEvent,
    VmachineIpaddrItem,
    VmachineSshEvent,
    VmachineBatchEvent,
    VmachineStatusEvent,
    VmachineCallBackEvent
)


def init_api(api: Api):
    api.add_resource(VmachineEvent, "/api/v1/vmachine")
    api.add_resource(VmachineBatchEvent, "/api/v1/vmachine/batch")
    api.add_resource(PreciseVmachineEvent, "/api/v1/vmachine/preciseget")
    api.add_resource(VmachineBatchDelayEvent, "/api/v1/vmachine/batch/delay")
    api.add_resource(VmachineItemForceEvent, "/api/v1/vmachine/<int:vmachine_id>/force")
    api.add_resource(VmachineDelayEvent, "/api/v1/vmachine/<int:vmachine_id>/delay")
    api.add_resource(VmachineIpaddrItem, "/api/v1/vmachine/<int:vmachine_id>/ipaddr")
    api.add_resource(VmachineSshEvent, "/api/v1/vmachine/<int:vmachine_id>/ssh")
    api.add_resource(VmachineItemEvent, "/api/v1/vmachine/<int:vmachine_id>")
    api.add_resource(VmachineControl, "/api/v1/vmachine/power")
    api.add_resource(AttachDevice, "/api/v1/vmachine/attach")
    api.add_resource(VnicEvent, "/api/v1/vnic")
    api.add_resource(VdiskEvent, "/api/v1/vdisk")
    api.add_resource(VmachineData, "/api/v1/vmachine/data")
    api.add_resource(VmachineItemData, "/api/v1/vmachine/<int:vmachine_id>/data")
    api.add_resource(VnicData, "/api/v1/vnic/data")
    api.add_resource(VnicItemData, "/api/v1/vnic/<int:vnic_id>/data")
    api.add_resource(VdiskData, "/api/v1/vdisk/data")
    api.add_resource(VdiskItemData, "/api/v1/vdisk/<int:vdisk_id>/data")
    api.add_resource(VmachineStatusEvent, "/api/v1/vmachine/update-status")
    api.add_resource(VmachineCallBackEvent, "/api/v1/vmachine/<int:vmachine_id>/callback")
