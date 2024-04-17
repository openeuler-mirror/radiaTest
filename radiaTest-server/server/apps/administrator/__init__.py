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
from server.apps.administrator.routes import Login, Org, OrgItem, ChangePasswd, PasswordRuleEvent, PasswordRuleItem


def init_api(api: Api):
    api.add_resource(Login, '/api/v1/admin/login', endpoint='admin_login')
    api.add_resource(Org, '/api/v1/admin/org', endpoint='admin_org')
    api.add_resource(OrgItem, '/api/v1/admin/org/<int:org_id>')
    api.add_resource(ChangePasswd, '/api/v1/admin/changepasswd')
    api.add_resource(PasswordRuleEvent, '/api/v1/admin/password-rule', methods=['GET', 'POST'])
    api.add_resource(PasswordRuleItem, '/api/v1/admin/<int:rule_id>/password-rule')
