# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
# http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author : 董霖峰
# @email : 1063183942@qq.com
# @Date : 2022/12/11 05:22:35
# @License : Mulan PSL v2
#####################################

from flask_restful import Api

from server.apps.manualjob.routes import (
    ManualJobEvent,
    ManualJobSubmitEvent,
    ManualJobLogEvent,
    ManualJobDeleteEvent,
    ManualJobLogQueryEvent
)


def init_api(api: Api):
    # 创建、查询手工测试任务(ManualJob).
    api.add_resource(ManualJobEvent, "/api/v1/ws/<str:workspace>/manual-job", methods=["POST", "GET"])
    # 提交完成执行指定id的手工测试任务.
    api.add_resource(ManualJobSubmitEvent, "/api/v1/manual-job/<int:manual_job_id>/submit", methods=["POST"])
    # 更新、删除指定id的手工测试任务的日志.
    api.add_resource(ManualJobLogEvent, "/api/v1/manual-job/log/<int:manual_job_id>", methods=["PUT", "DELETE"])
    # 删除指定id的手工测试任务(ManualJob).
    api.add_resource(ManualJobDeleteEvent, "/api/v1/manual-job/<int:manual_job_id>", methods=["DELETE"])
    # 查询指定id的手工测试任务的指定步骤的日志.
    api.add_resource(ManualJobLogQueryEvent, "/api/v1/manual-job/<int:manual_job_id>/step/<int:step_num>",
                     methods=["GET"])
