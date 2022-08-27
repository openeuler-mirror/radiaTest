from flask import jsonify

from server.model.qualityboard import Checklist
from server.utils.db import collect_sql_error
from server.utils.response_util import RET
from server.utils.page_util import PageUtil


class ChecklistHandler:
    @staticmethod
    @collect_sql_error
    def handler_get_one(checklist_id):
        _checklist = Checklist.query.get(checklist_id)
        if not _checklist:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="current checklist does not exist/already deleted"
            )
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=_checklist.to_json()
        )

    @staticmethod
    @collect_sql_error
    def handler_get_checklist(query):
        _filter = []
        if query.check_item:
            _filter.append(Checklist.check_item.like(f'%{query.check_item}%'))
        filter_chain = Checklist.query.filter(*_filter)
        page_dict, e = PageUtil.get_page_dict(filter_chain, query.page_num, query.page_size, func=lambda x: x.to_json())
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f'get checklist page error {e}'
            )
        return jsonify(
            error_code=RET.OK,
            error_msg='OK',
            data=page_dict
        )
