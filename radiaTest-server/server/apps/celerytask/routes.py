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

from flask_restful import Resource
from flask_pydantic import validate

from server.utils.auth_util import auth
from server.utils.response_util import response_collect
from server.schema.celerytask import CeleryTaskCreateSchema, CeleryTaskQuerySchema
from .handler import CeleryTaskHandler


class CeleryTaskEvent(Resource):
    @auth.login_required
    @response_collect
    @validate()
    def get(self, query: CeleryTaskQuerySchema):
        return CeleryTaskHandler.get_all(query)

    @auth.login_required
    @response_collect
    @validate()
    def post(self, body: CeleryTaskCreateSchema):
        return CeleryTaskHandler.create(body)