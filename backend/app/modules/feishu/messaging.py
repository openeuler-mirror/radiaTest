# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
import uuid

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

from app.modules.feishu.cards import build_home_card_content

# 飞书消息发送：封装 lark SDK 的卡片投递，失败抛 FeishuMessageSendError
# 供 bot_runtime 决定是否回退消息幂等 receipt。


class FeishuMessageSendError(Exception):
    """卡片投递失败，bot 层据此回退消息幂等以便重投重试。"""


class LarkMessageSender:
    """基于 lark SDK 的消息发送器，按 chat_id 或 open_id 投递 interactive 卡片。"""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

    def send_home_card(self, chat_id: str) -> None:
        self.send_card(chat_id, build_home_card_content())

    def send_card(self, chat_id: str, card: dict[str, object] | str) -> None:
        self._send_card(chat_id, "chat_id", card)

    def send_card_to_open_id(
        self,
        open_id: str,
        card: dict[str, object] | str,
    ) -> None:
        self._send_card(open_id, "open_id", card)

    def _send_card(
        self,
        receive_id: str,
        receive_id_type: str,
        card: dict[str, object] | str,
    ) -> None:
        content = card if isinstance(card, str) else json.dumps(card, ensure_ascii=False)
        body = (
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type("interactive")
            .content(content)
            .uuid(str(uuid.uuid4()))
            .build()
        )
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(body)
            .build()
        )
        response = self._client.im.v1.message.create(request)
        if not response.success():
            raise FeishuMessageSendError(
                f"send card failed: code={response.code} msg={response.msg} "
                f"log_id={response.get_log_id()}"
            )
