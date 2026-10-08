# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import logging
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.feishu.bot_runtime import start_feishu_bot
from app.modules.feishu.service import get_enabled_feishu_app_config

logger = logging.getLogger("kronos.bot")


def run_configured_bot_once() -> bool:
    """读取当前环境启用的飞书应用配置并启动 Bot 长连接。

    配置未启用时返回 False；返回 True 表示已接管连接。配置从数据库读取，
    读取后立即释放 Session，避免长连接进程长期持有数据库会话。
    """
    settings = get_settings()
    with SessionLocal() as db:
        config = get_enabled_feishu_app_config(db, environment=settings.app_env)
        if config is None:
            logger.info("Feishu bot is disabled or not configured for %s", settings.app_env)
            return False
        logger.info("Feishu bot config found for %s: app_id=%s", settings.app_env, config.app_id)
        app_id = config.app_id
        app_secret = config.app_secret

    start_feishu_bot(app_id=app_id, app_secret=app_secret)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("Starting radiaTest Feishu bot process")
    try:
        while True:
            if run_configured_bot_once():
                return
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping radiaTest Feishu bot process")


if __name__ == "__main__":
    main()
