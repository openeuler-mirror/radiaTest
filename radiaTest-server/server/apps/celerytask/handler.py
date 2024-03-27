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

from flask import jsonify, g

from server.utils.db import collect_sql_error, Insert
from server.model.celerytask import CeleryTask
from server.model.administrator import Admin
from server.utils.page_util import PageUtil
from server.utils.response_util import RET


class CeleryTaskHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = []

        admin = Admin.query.filter_by(account=g.user_login).first()
        if not admin:
            filter_params.append(CeleryTask.user_id == g.user_id)

        if query.tid:
            filter_params.append(CeleryTask.tid.like(f'%{query.tid}%'))
        
        if query.status:
            filter_params.append(CeleryTask.status == query.status)

        if query.object_type:
            filter_params.append(CeleryTask.object_type == query.object_type)

        query_filter = CeleryTask.query.filter(*filter_params).order_by(
            CeleryTask.create_time.desc(), CeleryTask.id.asc()
        )
        
        def page_func(item):
            celerytask_dict = item.to_dict()
            return celerytask_dict

        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get celery task page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)
    
    @staticmethod
    @collect_sql_error
    def create(body):
        return Insert(CeleryTask, body.__dict__).single(
            CeleryTask, "/celerytask"
        )

