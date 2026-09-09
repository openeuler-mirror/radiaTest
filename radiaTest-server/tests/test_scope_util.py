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
from server.utils.scope_util import ScopeKey


def test_gitee_scope_replaces_comma():
    assert ScopeKey.gitee("user.info,projects") == "user.info%20projects"


def test_oneid_scope_appends_state():
    assert ScopeKey.oneid("user.info,projects") == "user.info%20projects&state=random"


def test_scope_alias_bound():
    assert ScopeKey.gitee is ScopeKey.gitee_scope
    assert ScopeKey.oneid is ScopeKey.oneid_scope
