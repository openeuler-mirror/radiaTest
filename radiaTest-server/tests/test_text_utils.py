# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
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
from server.utils.text_utils import check_illegal_lables


def test_check_illegal_lables_strips_script():
    assert check_illegal_lables("<script>alert(1)</script>hello") == "hello"


def test_check_illegal_lables_keeps_plain_text():
    assert check_illegal_lables("plain text") == "plain text"


def test_check_illegal_lables_keeps_allowed_tag():
    assert check_illegal_lables("<p>hi</p>") == "<p>hi</p>"
