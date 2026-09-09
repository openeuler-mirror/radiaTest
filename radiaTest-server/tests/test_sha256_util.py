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
import base64

from server.utils.sha256_util import Hmacsha256


def test_encrypt_known_vector():
    signer = Hmacsha256("key")
    assert signer.encrypt(
        "The quick brown fox jumps over the lazy dog"
    ) == "97yD9DBThCSxMpjmqm+xQ+9NWaFJRhdZl0edvC0aPNg="


def test_encrypt_is_deterministic():
    signer = Hmacsha256("secret")
    assert signer.encrypt("content") == signer.encrypt("content")


def test_encrypt_differs_by_key():
    assert Hmacsha256("key1").encrypt("content") != Hmacsha256("key2").encrypt("content")


def test_encrypt_differs_by_content():
    assert Hmacsha256("key").encrypt("a") != Hmacsha256("key").encrypt("b")


def test_encrypt_returns_base64_of_32_bytes():
    sign = Hmacsha256("key").encrypt("content")
    assert len(base64.b64decode(sign)) == 32


def test_default_key_is_random_uuid():
    first = Hmacsha256()
    second = Hmacsha256()
    assert first.key != second.key
    assert first.encrypt("content") != second.encrypt("content")
