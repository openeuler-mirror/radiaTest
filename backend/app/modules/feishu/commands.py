# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from enum import StrEnum

# 飞书私聊命令解析：仅识别 help/帮助 回首页，其余文本交给远程命令/助手分支。


class FeishuBotAction(StrEnum):
    """私聊命令解析结果：回首页 或 忽略(进入后续分支)。"""

    SHOW_HOME = "show_home"
    IGNORE = "ignore"


HELP_COMMANDS = {"help", "帮助"}


def parse_private_text_command(text: str) -> FeishuBotAction:
    """把私聊文本归约为一个 bot 动作；大小写无关。"""
    command = text.strip().casefold()
    if command in HELP_COMMANDS:
        return FeishuBotAction.SHOW_HOME
    return FeishuBotAction.IGNORE
