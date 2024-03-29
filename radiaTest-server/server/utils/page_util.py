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

from flask import jsonify, current_app
from server.utils.response_util import RET


class PageUtil(object):
    def __init__(self, page_num=1, page_size=10):
        self.page_num = page_num
        self.page_size = page_size

    def get_page_dict(self, query_filter, model=None, func=None, is_set=False):
        try:
            page = query_filter.paginate(page=self.page_num, per_page=self.page_size)

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
    def page_func(item):
        """
        :description: convert item to json
        :param: item, object, item must has to_json function
        :return : data_dict, dict, dict result of item
        """
        data_dict = item.to_json()
        return data_dict

    @staticmethod
    def get_data(query_filter, query, func=None):
        """
        :description: get paged data
        :param: query_filter, object, sqlalchemy.BaseQuery
        :param: query, class, query contains page_num, page_size
        :param: func, function, the function can convert item to json
        :return : jsonify, contains paged data
        """
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

        if func is None:
            func = PageUtil.page_func

        page_dict, e = PageUtil(query.page_num, query.page_size).get_page_dict(query_filter, func=func)
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


class Paginate(object):
    def __init__(self, total, page_num=1, page_size=10):
        """
        :description: init paginate
        :param: total, int, total number of data records that will be paged
        :param: page_num, int, indicate the current page num
        :param: page_size, int, thr number of data per page
        """
        self._page = page_num
        self._per_page = page_size
        self._total = total
        if self._page > self.pages != 0:
            raise RuntimeError("page_num out of range.")
        if page_size == 0:
            raise RuntimeError("page_size can't be zero.")

    @property
    def has_next(self):
        return self._page < self.pages

    @property
    def has_prev(self):
        return self._page != 1 and self._page <= self.pages

    @property
    def next_num(self):
        if self.has_next:
            return self._page + 1
        else:
            return 0

    @property
    def prev_num(self):
        if self.has_prev:
            return self._page - 1
        else:
            return 0

    @property
    def per_page(self):
        return self._per_page

    @property
    def page(self):
        return self._page

    @property
    def pages(self):
        _pages = int(int(self._total) / self._per_page)
        if int(self._total) % self._per_page != 0:
            _pages += 1
        return _pages

    @property
    def total(self):
        return self._total

    @staticmethod
    def get_page_dict(total, data, page_num=1, page_size=10):
        """
        :description: get the current page data
        :param: total, int, total number of data records that will be paged
        :param: data, list, the current page data
        :param: page_num, int, indicate the current page num
        :param: page_size, int, thr number of data per page
        :return:
            page_dict: dict, the current page data and other datas about page
            e: error message
        """
        try:
            page = Paginate(total=total, page_num=page_num, page_size=page_size)

            if not page or int(page.total) <= 0:
                return {}, None
            page_dict = {
                "has_next": page.has_next,
                "has_prev": page.has_prev,
                "next_num": page.next_num,
                "prev_num": page.prev_num,
                "page_size": page.per_page,
                "pages": page.pages,
                "current_page": page.page,
                "total": page.total,
                "items": [] if data is None else data[
                    (page.page - 1) * page_size:page.page * page_size
                ]
            }
            return page_dict, None
        except Exception as e:
            current_app.logger.error(f"get page info error {e}")
            return {}, e
