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
from .routes import Cla, Group, Org, OrgStatistic


def init_api(api: Api):
    api.add_resource(Cla, '/api/v1/org/cla', '/api/v1/org/<int:org_id>/cla', endpoint='org_cla')
    api.add_resource(Group, '/api/v1/org/<int:org_id>/groups', endpoint='org_group')
    api.add_resource(Org, '/api/v1/orgs/all')
    api.add_resource(OrgStatistic, '/api/v1/org/<int:org_id>/statistic')
