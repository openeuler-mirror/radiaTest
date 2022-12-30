from flask import jsonify, current_app
from server.utils.response_util import RET


class PageUtil(object):
    @staticmethod
    def get_page_dict(query_filter, page_num=1, page_size=10, model=None, func=None, is_set=False):
        try:
            page = query_filter.paginate(page=page_num, per_page=page_size)

            if not page or page.total <= 0:
                return {}, None
            page_dict = {
                "has_next": page.has_next,
                "has_prev": page.has_prev,
                "next_num": page.next_num,
                "prev_num": page.prev_num,
                "page_size": page.per_page,
                "pages": page.pages,
                "current_page": page.page,
                "total": page.total
            }
            items = list()

            for item in page.items:
                item = func(item) if func else item.__dict__
                if not item:
                    continue
                items.append(item if not model else model(**item).dict())

            page_dict['items'] = items if not is_set else [dict(t) for t in {tuple(d.items()) for d in items}]
            return page_dict, None
        except Exception as e:
            current_app.logger.error(f"get page info error {e}")
            return {}, e

    @staticmethod
    def get_data(query_filter, query):
        if not query.paged:
            query_datas = query_filter.all()
            data = dict()
            items = []
            for _qd in query_datas:
                items.append(_qd.to_json())
            data.update(
                {
                    "total": query_filter.count(),
                    "items": items,
                }
            )
            return jsonify(error_code=RET.OK, error_msg="OK", data=data)

        def page_func(item):
            data_dict = item.to_json()
            return data_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, query.page_num, query.page_size, func=page_func
        )
        if e:
            return jsonify(
                error_code=RET.SERVER_ERR,
                error_msg=f"get page data error {e}"
            )

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=page_dict
        )