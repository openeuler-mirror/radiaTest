# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

import json
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

import lark_oapi as lark
from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.assistant.llm_client import (
    AssistantNotConfiguredError,
    LLMClientError,
    create_llm_client,
)
from app.modules.assistant.service import (
    AssistantContext,
    AssistantError,
    AssistantRunRequest,
    run_assistant,
)
from app.modules.assistant.tools import default_tool_registry
from app.modules.feishu.assistant_cards import (
    build_assistant_error_card,
    build_assistant_result_card,
)
from app.modules.feishu.card_actions import (
    FeishuCardAction,
    get_pending_remote_command,
    handle_card_action,
    remote_command_text_card,
)
from app.modules.feishu.commands import FeishuBotAction, parse_private_text_command
from app.modules.feishu.message_dedup import claim_feishu_message, release_feishu_message
from app.modules.feishu.messaging import FeishuMessageSendError, LarkMessageSender
from app.modules.feishu.service import get_bound_user_for_feishu_actor

logger = logging.getLogger("kronos.bot.feishu")

# 飞书 Bot 长连接运行时：接收私聊消息与卡片动作事件，解析后分发到对应处理器。
# 消息幂等由 message_dedup 在处理前 claim(INSERT 唯一约束)，处理失败时 release
# 回退，保证网络重投不会重复响应。卡片动作幂等由 card_actions 内的 idempotency
# 模块按 event_id 闭环。
SessionFactory = Callable[[], AbstractContextManager[Session]]


@dataclass(frozen=True)
class FeishuIncomingMessage:
    chat_id: str
    chat_type: str
    message_type: str
    text: str
    open_id: str | None
    union_id: str | None
    message_id: str | None = None


class FeishuMessageSender(Protocol):
    def send_home_card(self, chat_id: str) -> None:
        """发送主页卡片。"""
        raise NotImplementedError(self)

    def send_card(self, chat_id: str, card: dict[str, object] | str) -> None:
        """发送普通卡片。"""
        raise NotImplementedError(self)


def extract_text_content(content: str | None) -> str:
    if not content:
        return ""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return ""
    text = parsed.get("text")
    return text if isinstance(text, str) else ""


def parse_sdk_event(event: object) -> FeishuIncomingMessage | None:
    event_body = getattr(event, "event", None)
    sender = getattr(event_body, "sender", None)
    message = getattr(event_body, "message", None)
    if message is None:
        return None

    sender_id = getattr(sender, "sender_id", None)
    chat_id = getattr(message, "chat_id", None)
    chat_type = getattr(message, "chat_type", None)
    message_type = getattr(message, "message_type", None)
    if not chat_id or not chat_type or not message_type:
        return None

    return FeishuIncomingMessage(
        chat_id=chat_id,
        chat_type=chat_type,
        message_type=message_type,
        text=extract_text_content(getattr(message, "content", None)),
        open_id=getattr(sender_id, "open_id", None),
        union_id=getattr(sender_id, "union_id", None),
        message_id=getattr(message, "message_id", None),
    )


def parse_card_action_event(event: object) -> FeishuCardAction | None:
    header = getattr(event, "header", None)
    event_id = getattr(header, "event_id", None) or getattr(event, "event_id", None)
    if not isinstance(event_id, str):
        event_id = None
    event_body = getattr(event, "event", None)
    operator = getattr(event_body, "operator", None)
    action = getattr(event_body, "action", None)
    value = getattr(action, "value", None)
    if isinstance(value, dict):
        action_name = value.get("action")
        if not isinstance(action_name, str) or not action_name:
            return None
        form_value = getattr(action, "form_value", None)
        if isinstance(form_value, dict):
            value = {**value, "form_value": form_value}
        return FeishuCardAction(
            action=action_name,
            value=value,
            open_id=getattr(operator, "open_id", None),
            union_id=getattr(operator, "union_id", None),
            event_id=event_id,
        )

    action_tag = getattr(action, "tag", None)
    if action_tag not in {"select_static", "input"}:
        return None
    action_name = "vm_create_form_update"
    input_name = getattr(action, "name", None)
    if isinstance(input_name, str):
        if input_name.startswith("pipeline_"):
            action_name = "pipeline_trigger_form_update"
        elif action_tag == "input" and input_name.startswith("remote_command|"):
            action_name = "remote_command_form_update"
    return FeishuCardAction(
        action=action_name,
        value={
            "tag": action_tag,
            "name": input_name,
            "option": getattr(action, "option", None),
            "input_value": getattr(action, "input_value", None),
        },
        open_id=getattr(operator, "open_id", None),
        union_id=getattr(operator, "union_id", None),
        event_id=event_id,
    )


def card_response(card: dict[str, object]) -> P2CardActionTriggerResponse:
    return P2CardActionTriggerResponse({"card": {"type": "raw", "data": card}})


def toast_response(content: str, *, toast_type: str = "warning") -> P2CardActionTriggerResponse:
    return P2CardActionTriggerResponse({"toast": {"type": toast_type, "content": content}})


class FeishuBotHandler:
    def __init__(
        self,
        sender: FeishuMessageSender,
        *,
        session_factory: SessionFactory = SessionLocal,
    ) -> None:
        self._sender = sender
        self._session_factory = session_factory

    def handle_sdk_event(self, event: object) -> None:
        """处理一条飞书消息事件：先 claim 幂等，再分发，失败回退 claim。

        飞书在未收到 ack 或网络抖动时会重投同一消息；claim_feishu_message
        用 message_id 的唯一约束保证只处理一次。发送失败或异常时 release，
        让后续重投可重新处理(发送成功则保留 receipt 永久去重)。
        """
        message = parse_sdk_event(event)
        if message is None:
            logger.info("Ignored malformed Feishu message event")
            return
        if message.message_id:
            with self._session_factory() as db:
                if not claim_feishu_message(db, message.message_id):
                    logger.info(
                        "Ignored duplicate Feishu message: message_id=%s",
                        message.message_id,
                    )
                    return
        try:
            self.handle_message(message)
        except FeishuMessageSendError:
            if message.message_id:
                with self._session_factory() as db:
                    release_feishu_message(db, message.message_id)
            logger.exception("Failed to send Feishu message")
        except Exception:
            if message.message_id:
                with self._session_factory() as db:
                    release_feishu_message(db, message.message_id)
            raise

    def handle_message(self, message: FeishuIncomingMessage) -> None:
        """分发私聊文本消息：help 命令回首页卡，否则进入远程命令或智能助手分支。

        非 p2p、非文本消息忽略。当无远程命令待执行且未配置 LLM 助手时，
        不在飞书侧建任何卡片，避免无意义响应。
        """
        if message.chat_type != "p2p":
            logger.info("Ignored non-private Feishu message: chat_type=%s", message.chat_type)
            return
        if message.message_type != "text":
            logger.info("Ignored non-text Feishu message: message_type=%s", message.message_type)
            return

        action = parse_private_text_command(message.text)
        if action != FeishuBotAction.SHOW_HOME:
            if not message.open_id:
                return
            settings = get_settings()
            if (
                not settings.llm_assistant_enabled
                and get_pending_remote_command(message.open_id) is None
            ):
                return
            with self._session_factory() as db:
                card = remote_command_text_card(
                    db,
                    open_id=message.open_id,
                    union_id=message.union_id,
                    command=message.text,
                )
                if card is None:
                    user = get_bound_user_for_feishu_actor(
                        db,
                        open_id=message.open_id,
                        union_id=message.union_id,
                    )
                    if user is None:
                        from app.modules.feishu.cards import build_unbound_card

                        card = build_unbound_card()
                    else:
                        try:
                            result = run_assistant(
                                request=AssistantRunRequest(
                                    db=db,
                                    context=AssistantContext(
                                        user=user,
                                        channel="feishu",
                                        conversation_id=message.chat_id,
                                    ),
                                    text=message.text,
                                    client=create_llm_client(settings),
                                    registry=default_tool_registry(),
                                    max_rounds=settings.llm_max_tool_rounds,
                                ),
                            )
                            card = build_assistant_result_card(result)
                        except AssistantNotConfiguredError:
                            card = build_assistant_error_card(
                                "智能助手尚未配置，请使用首页中的确定性功能。"
                            )
                        except (AssistantError, LLMClientError):
                            logger.exception("Failed to handle Feishu assistant message")
                            card = build_assistant_error_card("请求处理失败，请稍后重试。")
            if card is not None:
                self._sender.send_card(message.chat_id, card)
            return

        logger.info(
            "Sending Feishu home card: chat_id=%s open_id=%s union_id=%s",
            message.chat_id,
            message.open_id,
            message.union_id,
        )
        self._sender.send_home_card(message.chat_id)

    def handle_card_action_event(self, event: object) -> P2CardActionTriggerResponse:
        """处理卡片按钮/表单动作事件，返回新的卡片内容(toast 或整卡更新)。

        解析失败返回 toast 提示；处理异常统一返回错误 toast 并记日志，
        不向飞书抛异常(长连接回调无法重试，只能靠用户重新操作)。
        """
        action = parse_card_action_event(event)
        if action is None:
            logger.info("Ignored malformed Feishu card action event")
            return toast_response("无法识别的操作")

        logger.info(
            "Handling Feishu card action: action=%s open_id=%s union_id=%s",
            action.action,
            action.open_id,
            action.union_id,
        )
        try:
            with self._session_factory() as db:
                return card_response(handle_card_action(db, action))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to handle Feishu card action")
            return toast_response("操作失败，请查看 radiaTest Bot 日志", toast_type="error")


def start_feishu_bot(app_id: str, app_secret: str) -> None:
    """构建并启动飞书长连接 Bot：注册消息与卡片动作回调，阻塞运行。"""
    sender = LarkMessageSender(app_id=app_id, app_secret=app_secret)
    handler = FeishuBotHandler(sender)
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(handler.handle_sdk_event)
        .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(lambda _: None)
        .register_p2_card_action_trigger(handler.handle_card_action_event)
        .build()
    )
    client = lark.ws.Client(app_id, app_secret, event_handler=event_handler)
    client.start()
