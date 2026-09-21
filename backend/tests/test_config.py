# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from app.core.config import Settings


def test_default_jwt_access_token_expire_minutes_is_one_day() -> None:
    settings = Settings()

    assert settings.jwt_access_token_expire_minutes == 1440


def test_default_display_timezone_is_asia_shanghai() -> None:
    settings = Settings()

    assert settings.display_timezone == "Asia/Shanghai"


def test_empty_cors_origins_env_means_no_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "")

    settings = Settings()

    assert settings.cors_origins == []


def test_cors_origins_env_accepts_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")

    settings = Settings()

    assert settings.cors_origins == ["https://a.example", "https://b.example"]
