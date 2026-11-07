"""AI 教学聊天接口：会话管理与 Agent 流式回复（阶段 8 / 阶段 10）。

流式接口事件（SSE，保持阶段 7/8 的事件名，仅增加元数据字段）：
- event: start / data: {"conversation_id", "user_message_id", "model", "title",
                         "intent", "sub_intent"}
- event: delta / data: {"text": "增量文本"}
- event: done  / data: {"conversation_id", "message_id", "model", "title",
                         "message_count", "intent", "sub_intent", "subgraph",
                         "result_status"}
- event: error / data: {"conversation_id", "message_id", "message"}

非教学子图不调用模型，start/done 中的 model 为 null。
用户消息与 AI 回复均持久化；模型失败、Agent 超时或生成中断时保存
status=error 的助手消息（保留已生成部分文本），并通过 error 事件明确提示，
不伪造回复。
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent.contracts import AgentRunError
from app.agent.runner import AgentService
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    MessageCreate,
)
from app.services.conversation_service import ConversationService
from app.services.llm_client import LlmError

logger = logging.getLogger("xiaoma.conversation")

router = APIRouter(prefix="/conversations", tags=["conversations"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # 关闭反向代理缓冲，保证逐段输出
}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("", response_model=ConversationDetailOut, status_code=201)
def create_conversation(
    payload: ConversationCreate, db: Session = Depends(get_db)
) -> ConversationDetailOut:
    """新建聊天会话（可关联知识点/每日任务）；已有会话不受影响。"""
    return ConversationService(db).create_conversation(payload)


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)) -> list[ConversationOut]:
    """查询聊天历史列表（最近活动在前）。"""
    return ConversationService(db).list_conversations()


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: uuid.UUID, db: Session = Depends(get_db)
) -> ConversationDetailOut:
    """查看会话及其全部持久化消息（用于刷新后继续阅读/继续对话）。"""
    return ConversationService(db).get_conversation(conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    """物理删除聊天会话及其全部消息（不可恢复），其他会话不受影响。"""
    ConversationService(db).delete_conversation(conversation_id)
    return Response(status_code=204)


@router.post("/{conversation_id}/messages/stream")
def send_message_stream(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    # 流式生成期间仍需使用数据库会话保存 AI 回复，故依赖随请求生命周期释放
    db: Session = Depends(get_db, scope="request"),
) -> StreamingResponse:
    """发送用户消息，由主 Agent 路由到子图并以 SSE 流式返回回复。"""
    run = AgentService(db).start(conversation_id, payload.content)
    context = run.chat_context

    def _persist_error(message: str) -> str | None:
        """保存失败回复；持久化自身出错不影响向用户发送错误提示。"""
        try:
            saved = run.fail(message)
            return str(saved.id)
        except Exception:
            logger.exception(
                "保存失败回复时出错: conversation_id=%s", context.conversation.id
            )
            return None

    async def event_source() -> AsyncIterator[str]:
        yield _sse(
            "start",
            {
                "conversation_id": str(context.conversation.id),
                "user_message_id": str(context.user_message.id),
                "model": run.message_model_name,
                "title": context.conversation.title,
                "intent": run.intent.intent,
                "sub_intent": run.intent.sub_intent,
            },
        )
        done_event: dict | None = None
        try:
            async for event in run.astream():
                if event["event"] == "delta":
                    yield _sse("delta", {"text": event["delta"]})
                elif event["event"] == "done":
                    done_event = event
        except LlmError as exc:
            llm_request = context.llm_request
            logger.warning(
                "AI 教学回复失败: provider=%s model=%s error=%s",
                llm_request.provider if llm_request else None,
                context.model_name,
                exc.message,
            )
            message_id = _persist_error(exc.message)
            yield _sse(
                "error",
                {
                    "conversation_id": str(context.conversation.id),
                    "message_id": message_id,
                    "message": exc.message,
                },
            )
            return
        except AgentRunError as exc:
            logger.warning(
                "Agent 执行失败: conversation_id=%s error=%s",
                context.conversation.id,
                exc.message,
            )
            message_id = _persist_error(exc.message)
            yield _sse(
                "error",
                {
                    "conversation_id": str(context.conversation.id),
                    "message_id": message_id,
                    "message": exc.message,
                },
            )
            return
        except (asyncio.CancelledError, GeneratorExit):
            # 客户端断开/服务关闭：保留已生成部分并标记中断，然后按原语义退出
            _persist_error("回复生成已中断")
            raise
        except Exception:
            logger.exception(
                "Agent 流式调用未处理异常: conversation_id=%s",
                context.conversation.id,
            )
            message_id = _persist_error("服务器内部错误，请稍后重试")
            yield _sse(
                "error",
                {
                    "conversation_id": str(context.conversation.id),
                    "message_id": message_id,
                    "message": "服务器内部错误，请稍后重试",
                },
            )
            return

        if done_event is None:
            # 理论上不会发生；仍按失败处理，绝不把不完整结果标记为成功
            message_id = _persist_error("Agent 未返回完成状态")
            yield _sse(
                "error",
                {
                    "conversation_id": str(context.conversation.id),
                    "message_id": message_id,
                    "message": "Agent 未返回完成状态，请重试",
                },
            )
            return

        try:
            message = run.complete()
        except Exception:
            # 内容已生成但落库失败：不能伪装成成功，明确提示用户重试
            logger.exception(
                "保存 AI 回复失败: conversation_id=%s", context.conversation.id
            )
            yield _sse(
                "error",
                {
                    "conversation_id": str(context.conversation.id),
                    "message_id": None,
                    "message": "回复已生成但保存失败，请重试",
                },
            )
            return
        yield _sse(
            "done",
            {
                "conversation_id": str(context.conversation.id),
                "message_id": str(message.id),
                "model": run.message_model_name,
                "title": context.conversation.title,
                "message_count": context.learning_session.message_count,
                "intent": done_event.get("intent"),
                "sub_intent": done_event.get("sub_intent"),
                "subgraph": done_event.get("subgraph"),
                "result_status": done_event.get("result_status"),
            },
        )

    return StreamingResponse(
        event_source(), media_type="text/event-stream", headers=SSE_HEADERS
    )
