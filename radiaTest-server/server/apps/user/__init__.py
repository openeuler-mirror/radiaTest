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
from .routes import OauthLogin, Login, UserPrivate
from .routes import UserSearch
from .routes import UserItem
from .routes import Org
from .routes import Logout
from .routes import Group
from .routes import UserTask
from .routes import UserPrivacySign


def init_api(api: Api):
    api.add_resource(OauthLogin, '/api/v1/oauth/login', endpoint='user_login')
    api.add_resource(Login, '/api/v1/login', endpoint='login')
    api.add_resource(UserSearch, '/api/v1/users', endpoint="user")
    api.add_resource(UserItem, '/api/v1/users/<string:user_id>', endpoint='useritem')
    api.add_resource(Org, '/api/v1/users/org/<int:org_id>/<string:org_name>', endpoint='user_org')
    api.add_resource(Logout, '/api/v1/logout', endpoint='logout')
    api.add_resource(Group, '/api/v1/users/groups/<int:group_id>', endpoint='user_group')
    api.add_resource(UserTask, '/api/v1/user/task/info', endpoint='user_task')
    api.add_resource(UserPrivate, '/api/v1/user/private/<string:user_id>', endpoint='user_private')
    api.add_resource(UserPrivacySign, '/api/v1/user/privacy-sign', endpoint='privacy_sign')
