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
from .routes import OauthLogin, Login
from .routes import User
from .routes import UserItem
from .routes import Org
from .routes import Logout
from .routes import Group
from .routes import UserTask
from .routes import UserMachine
from .routes import UserCaseCommit
from .routes import UserAssetRank


def init_api(api: Api):
    api.add_resource(OauthLogin, '/api/v1/oauth/login', endpoint='user_login')
    api.add_resource(Login, '/api/v1/login', endpoint='login')
    api.add_resource(User, '/api/v1/users', endpoint="user")
    api.add_resource(UserItem, '/api/v1/users/<string:user_id>', endpoint='useritem')
    api.add_resource(Org, '/api/v1/users/org/<int:org_id>', endpoint='user_org')
    api.add_resource(Logout, '/api/v1/logout', endpoint='logout')
    api.add_resource(Group, '/api/v1/users/groups/<int:group_id>', endpoint='user_group')
    api.add_resource(UserTask, '/api/v1/user/task/info', endpoint='user_task')
    api.add_resource(UserMachine, '/api/v1/user/machine/info', endpoint='user_machine')
    api.add_resource(UserCaseCommit, '/api/v1/user/case/commit', endpoint='user_case_commit')
    api.add_resource(UserAssetRank, '/api/v1/user/rank')