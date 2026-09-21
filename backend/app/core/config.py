# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from functools import lru_cache
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置：全部来自环境变量或 .env，大小写不敏感。

    敏感项(jwt_secret_key、resource_secret_key、database_url)必须由部署环境
    注入，默认值仅用于本地占位，不得用于生产。lru_cache 保证进程内单例，
    测试改配置后需 get_settings.cache_clear()。
    """

    app_env: str = "development"
    app_name: str = "kronos"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://kronos:change-me@localhost:5432/kronos_dev"
    test_database_url: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    jwt_secret_key: str = "change-me-change-me-change-me-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    resource_secret_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    vm_image_repo_root: str = (
        "http://172.168.131.94:9400/repo_list/mugen.mirror"
    )
    vm_openeuler_update_repo_root: str = "http://121.36.84.172/repo.openeuler.org"
    vm_dailybuild_repo_root: str = "http://121.36.84.172/dailybuild"
    install_mirror_base: str = "http://172.168.131.94:9400/repo_list/iteration.repo"
    # RC 版本软件包比对：公网 dailybuild 构建根（唯一含 source 树的位置），
    # 目录列表 title=/href= 双正则抓取；缓存与导出产物落盘目录。
    rc_dailybuild_base_url: str = "http://121.36.84.172/dailybuild"
    rc_pkglist_cache_dir: str = "/data/rc-pkglist-cache"
    rc_export_dir: str = "/data/rc-exports"
    vm_default_dist: str = "openEuler"
    vm_default_ssh_username: str = "root"
    vm_default_ssh_password: str = "openEuler12#$"
    vm_dhcp_leases_url: str = "http://172.168.131.94:9400/dhcpd.leases"
    vm_network_bridge: str = "br0"
    vm_max_concurrent_per_host: int = 4
    vm_iso_upload_dir: str = "/var/lib/kronos/uploads"
    display_timezone: str = "Asia/Shanghai"
    vm_host_ssh_key_path: str | None = "/etc/kronos/ssh/id_rsa"
    vm_host_script_timeout_seconds: int = 4200
    mugen_repo_url: str = "https://atomgit.com/openeuler/mugen.git"
    mugen_repo_branch: str = "master"
    mugen_sync_lock_ttl_seconds: int = 1800
    pipeline_log_dir: str = "/data/test-logs"
    llm_assistant_enabled: bool = False
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = 30
    llm_max_tool_rounds: int = Field(default=6, ge=1, le=12)
    admin_username: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """CORS 允许用逗号分隔的字符串配置多个来源。"""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("display_timezone", mode="before")
    @classmethod
    def validate_display_timezone(cls, value: object) -> str:
        """展示时区必须是合法 IANA 时区，否则启动即失败，避免静默用错时区。"""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("display_timezone must be a valid IANA timezone")
        timezone_name = value.strip()
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("display_timezone must be a valid IANA timezone") from exc
        return timezone_name

    @field_validator(
        "celery_broker_url",
        "celery_result_backend",
        "vm_host_ssh_key_path",
        "llm_base_url",
        "llm_api_key",
        "llm_model",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
