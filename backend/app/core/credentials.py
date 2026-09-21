# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings

# 凭据加解密：资源 SSH/BMC 密码以 Fernet 密文存库，密钥即 RESOURCE_SECRET_KEY。
# 密钥变更会导致历史密文无法解密(read_resource_credentials 抛 CredentialReadError)，
# 因此密钥一经设定不可随意更换；如需轮换必须重新录入全部凭据。


@lru_cache
def get_credential_cipher() -> Fernet:
    """按 RESOURCE_SECRET_KEY 构建单例 Fernet，进程内复用避免重复构建。"""
    return Fernet(get_settings().resource_secret_key.encode())


def encrypt_secret(value: str | None) -> str | None:
    """加密明文凭据为可入库的密文字符串，None 原样返回。"""
    if value is None:
        return None
    return get_credential_cipher().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    """解密密文为明文，空值原样返回。密钥不一致时会抛 InvalidToken。"""
    if not value:
        return None
    return get_credential_cipher().decrypt(value.encode()).decode()
