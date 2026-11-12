"""Agent 运行器（阶段 10）：准备会话、执行主图、超时与日志、持久化入口。

职责边界：
- AgentService 在准备阶段完成意图识别与 ChatContext 构建（用户消息由
  ConversationService 保存）；
- AgentRun 执行 LangGraph 主图，逐段产出 delta 事件，最后产出 done 事件；
- API 层负责把事件写成 SSE，并在成功/失败/中断时调用 complete()/fail()，
  确保历史聊天与失败状态都能持久化；
- 日志只记录会话 ID、意图、子图、状态与耗时，不记录用户消息、提示词或密钥。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.agent.contracts import AgentRunError, IntentResult
from app.agent.graph import build_agent_graph
from app.agent.intent import recognize_intent
from app.core.config import get_settings
from app.models.conversation import Message
from app.schemas.cards import normalize_card
from app.services.conversation_service import (
    ChatContext,
    ConversationService,
)
from app.services.llm_client import LlmError

logger = logging.getLogger("xiaoma.agent")


class AgentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start(self, conversation_id: uuid.UUID, content: str) -> "AgentRun":
        """意图识别 → 准备会话 → 返回可流式执行的 AgentRun。

        只有教学意图需要模型；计划、测验、错题、资源查询在未配置模型时
        仍可正常使用。
        """
        intent = recognize_intent(content)
        service = ConversationService(self.db)
        context = service.prepare_chat(
            conversation_id,
            content,
            require_llm=intent.intent == "teaching",
        )
        run = AgentRun(db=self.db, chat_context=context, intent=intent)
        run.assistant_message = service.begin_assistant_message(context)
        return run

    def start_regenerate(
        self, conversation_id: uuid.UUID, message_id: uuid.UUID
    ) -> "AgentRun":
        """V1.4：重新生成一条普通文本回复，复用原始用户消息。

        不新增用户消息行、不重复增加 message_count；上下文截止到该用户消息，
        旧回复不进入模型上下文。
        """
        service = ConversationService(self.db)
        content, source = service.get_regeneration_source(
            conversation_id, message_id
        )
        intent = recognize_intent(content)
        context = service.prepare_chat(
            conversation_id,
            content,
            require_llm=intent.intent == "teaching",
            existing_user_message=source,
        )
        run = AgentRun(db=self.db, chat_context=context, intent=intent)
        run.assistant_message = service.begin_assistant_message(context)
        return run


@dataclass
class AgentRun:
    db: Session
    chat_context: ChatContext
    intent: IntentResult
    _parts: list[str] = field(default_factory=list, init=False)
    _cards: list[dict[str, Any]] = field(default_factory=list, init=False)
    # 生成开始时预建的 streaming 消息；卡片事件与终态都落在同一行
    assistant_message: Message | None = None

    @property
    def reply(self) -> str:
        return "".join(self._parts)

    @property
    def cards(self) -> list[dict[str, Any]]:
        return self._cards

    @property
    def message_model_name(self) -> str | None:
        """教学回答记录实际模型名；数据类回答不调用模型，记录为空。"""
        return (
            self.chat_context.model_name
            if self.intent.intent == "teaching"
            else None
        )

    async def astream(self) -> AsyncIterator[dict[str, Any]]:
        """执行主 Agent，产出 {"event": "delta"} 与 {"event": "done"}。"""
        settings = get_settings()
        timeout_seconds = settings.xiaoma_agent_timeout_seconds
        conversation_id = self.chat_context.conversation.id
        started = time.perf_counter()

        graph = build_agent_graph(db=self.db)
        initial_state = {
            "user_message": self.chat_context.user_message.content,
            "messages": self.chat_context.messages,
            "chat_context": self.chat_context,
            "intent": self.intent,
        }
        final_state: dict[str, Any] = {}

        logger.info(
            "agent run start conversation_id=%s intent=%s sub_intent=%s",
            conversation_id,
            self.intent.intent,
            self.intent.sub_intent,
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                async for mode, chunk in graph.astream(
                    initial_state, stream_mode=["custom", "values"]
                ):
                    if mode == "custom":
                        if isinstance(chunk, dict) and chunk.get("delta"):
                            text = str(chunk["delta"])
                            self._parts.append(text)
                            yield {"event": "delta", "delta": text}
                        elif isinstance(chunk, dict) and "card" in chunk:
                            # V1.4：卡片一次性完整下发；不合法帧降级 error_card
                            card = normalize_card(chunk["card"])
                            self._cards.append(card)
                            yield {"event": "card", "card": card}
                    elif mode == "values":
                        final_state = chunk
        except TimeoutError:
            logger.warning(
                "agent run timeout conversation_id=%s intent=%s timeout=%ss",
                conversation_id,
                self.intent.intent,
                timeout_seconds,
            )
            raise AgentRunError(
                f"Agent 执行超时（超过 {timeout_seconds:g} 秒），已停止本次处理，"
                "请稍后重试。"
            ) from None
        except AgentRunError:
            raise
        except LlmError:
            # 模型错误的统一中文提示与密钥脱敏由 LlmError 负责，API 原样展示。
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "agent run failed conversation_id=%s intent=%s",
                conversation_id,
                self.intent.intent,
            )
            raise AgentRunError("Agent 执行失败，请稍后重试。") from None

        if not self.reply.strip() and final_state.get("reply"):
            # 兜底：若流式增量因运行时原因丢失，最终状态中的完整回复仍要送达，
            # 不能出现「已生成但用户无响应」。记录 warning 便于定位流式问题。
            logger.warning(
                "agent stream missing deltas, fallback to final reply: "
                "conversation_id=%s intent=%s",
                conversation_id,
                self.intent.intent,
            )
            text = str(final_state["reply"])
            self._parts.append(text)
            yield {"event": "delta", "delta": text}

        # 纯卡片回复也是有效回复（例如只下发一张今日任务卡片）
        if not self.reply.strip() and not self._cards:
            logger.warning(
                "agent run empty conversation_id=%s intent=%s",
                conversation_id,
                self.intent.intent,
            )
            raise AgentRunError("没有生成有效回复，请稍后重试。")

        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "agent run done conversation_id=%s intent=%s subgraph=%s status=%s "
            "duration_ms=%d",
            conversation_id,
            self.intent.intent,
            final_state.get("subgraph", self.intent.intent),
            final_state.get("result_status", "ok"),
            duration_ms,
        )
        yield {
            "event": "done",
            "intent": self.intent.intent,
            "sub_intent": self.intent.sub_intent,
            "subgraph": final_state.get("subgraph", self.intent.intent),
            "result_status": final_state.get("result_status", "ok"),
            "model": self.message_model_name,
        }

    # ------------------------------------------------------------- 持久化

    def complete(self):
        """保存完整成功回复（含本轮收到的全部卡片）。"""
        return ConversationService(self.db).complete_assistant_message(
            self.chat_context,
            self.reply,
            model_name=self.message_model_name,
            assistant_message=self.assistant_message,
            cards=self._cards,
        )

    def fail(self, error_message: str):
        """保存失败回复（保留已生成的部分内容）。"""
        return ConversationService(self.db).fail_assistant_message(
            self.chat_context,
            self.reply,
            error_message,
            model_name=self.message_model_name,
            assistant_message=self.assistant_message,
        )

    def stop(self):
        """V1.4：保存用户主动停止的回复，状态 stopped，不伪装成功。"""
        return ConversationService(self.db).stop_assistant_message(
            self.chat_context,
            self.reply,
            model_name=self.message_model_name,
            assistant_message=self.assistant_message,
        )
