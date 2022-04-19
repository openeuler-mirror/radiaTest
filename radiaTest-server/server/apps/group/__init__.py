# Copyright (c) [2021] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
from .routes import Group, User

def init_api(api: Api):
    api.add_resource(Group, '/api/v1/groups', '/api/v1/groups/<int:group_id>', endpoint='group')
    # api.add_resource(OrgGroups, '/api/v1/org/<int:org_id>/groups/all')
    api.add_resource(User, '/api/v1/groups/<int:group_id>/users', endpoint='group_user')
