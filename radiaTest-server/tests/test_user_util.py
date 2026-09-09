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
from server.utils.user_util import ProfileMap


def test_gitee_user_mapping():
    profile = ProfileMap.gitee_user(
        {"id": 1, "login": "l", "name": "n", "avatar_url": "http://a/1.png"}
    )
    assert profile == {
        "user_id": "gitee_1",
        "user_login": "l",
        "user_name": "n",
        "avatar_url": "http://a/1.png",
    }


def test_gitee_user_id_converted_to_str():
    profile = ProfileMap.gitee_user({"id": 123})
    assert profile["user_id"] == "gitee_123"


def test_oneid_user_mapping():
    profile = ProfileMap.oneid_user(
        {"sub": "u1", "username": "bob", "picture": "http://a/2.png"}
    )
    assert profile == {
        "user_id": "oneid_u1",
        "user_login": "bob",
        "user_name": "bob",
        "avatar_url": "http://a/2.png",
    }


def test_user_profile_with_missing_fields():
    assert ProfileMap.gitee_user({}) == {
        "user_id": "gitee_None",
        "user_login": None,
        "user_name": None,
        "avatar_url": None,
    }
