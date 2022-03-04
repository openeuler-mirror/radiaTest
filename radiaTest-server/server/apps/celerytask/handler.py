from flask import jsonify, g
from sqlalchemy import or_

from server.utils.db import collect_sql_error
from server.model.celerytask import CeleryTask
from server.schema.celerytask import CeleryTaskQuerySchema
from server.utils.page_util import PageUtil
from server.utils.response_util import RET


class CeleryTaskHandler:
    @staticmethod
    @collect_sql_error
    def get_all(query):
        filter_params = [
            CeleryTask.user_id == int(g.gitee_id),
        ]

        if query.tid:
            filter_params.append(CeleryTask.tid.like(f'%{query.tid}%'))
        
        if query.status:
            filter_params.append(CeleryTask.status == query.status)

        if query.object_type:
            filter_params.append(CeleryTask.object_type == query.object_type)

        query_filter = CeleryTask.query.filter(*filter_params).order_by(CeleryTask.create_time.desc())
        
        def page_func(item):
            celerytask_dict = item.to_dict()
            return celerytask_dict

        page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get celery task page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)

