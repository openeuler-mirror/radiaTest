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
from server.utils.math_util import calculate_rate


def test_calculate_rate_with_decimal():
    assert calculate_rate(1, 4, 2) == "25.00%"


def test_calculate_rate_default_decimal():
    assert calculate_rate(1, 3) == "33%"


def test_calculate_rate_zero_number():
    assert calculate_rate(0, 5, 1) == "0.0%"


def test_calculate_rate_zero_total_returns_none():
    assert calculate_rate(1, 0) is None


def test_calculate_rate_accepts_string_input():
    assert calculate_rate("2", "8", 0) == "25%"
