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
    UpdateTaskEvent,
    LoginOrgList,
    VmachineExist,
    CaCert,
    DailyBuildEvent,
    RpmCheckEvent,
)


def init_api(api: Api):
    api.add_resource(UpdateTaskEvent, "/api/v1/openeuler/task/update")
    api.add_resource(LoginOrgList, "/api/v1/login/org/list")
    api.add_resource(VmachineExist, "/api/v1/vmachine/check-exist")
    api.add_resource(CaCert, "/api/v1/ca-cert")
    api.add_resource(DailyBuildEvent, "/api/v1/dailybuild")
    api.add_resource(RpmCheckEvent, "/api/v1/rpmcheck")
