# Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
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
# @Date    : 2026/09/09
# @License : Mulan PSL v2
#####################################
import pytest

from server.utils.page_util import Paginate


def test_pages_round_up():
    assert Paginate(total=95, page_num=1, page_size=10).pages == 10


def test_pages_exact_division():
    assert Paginate(total=100, page_num=1, page_size=10).pages == 10


def test_total_zero_means_no_pages():
    page = Paginate(total=0, page_num=1, page_size=10)
    assert page.pages == 0
    assert page.has_next is False
    assert page.next_num == 0


def test_middle_page_navigation():
    page = Paginate(total=95, page_num=3, page_size=10)
    assert page.has_next is True
    assert page.next_num == 4
    assert page.has_prev is True
    assert page.prev_num == 2


def test_first_page_has_no_prev():
    page = Paginate(total=95, page_num=1, page_size=10)
    assert page.has_prev is False
    assert page.prev_num == 0


def test_page_num_out_of_range():
    with pytest.raises(RuntimeError, match="out of range"):
        Paginate(total=95, page_num=11, page_size=10)


def test_page_size_zero():
    # page_size=0 时 pages 计算先于零值校验执行，抛出除零异常
    with pytest.raises(ZeroDivisionError):
        Paginate(total=95, page_num=1, page_size=0)


def test_get_page_dict_returns_current_page():
    data = list(range(5))
    page_dict, e = Paginate.get_page_dict(total=5, data=data, page_num=1, page_size=2)
    assert e is None
    assert page_dict["items"] == [0, 1]
    assert page_dict["total"] == 5
    assert page_dict["pages"] == 3
    assert page_dict["has_next"] is True
    assert page_dict["current_page"] == 1


def test_get_page_dict_with_empty_data():
    page_dict, e = Paginate.get_page_dict(total=0, data=[], page_num=1, page_size=10)
    assert e is None
    assert page_dict == {}
