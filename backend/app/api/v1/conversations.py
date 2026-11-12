"""AI 教学聊天接口：会话管理、Agent 流式回复与 V1.4 卡片/消息操作。

SSE 事件（阶段 7/8 事件名保持不变，V1.4 增加元数据字段）：
- event: start / data: {"conversation_id", "user_message_id", "message_id",
                         "model", "title", "intent", "sub_intent"}
- event: delta / data: {"text": "增量文本"}
- event: card  / data: {"conversation_id", "message_id", "card_version",
                         "message_type", "structured_data"}   ← V1.4 新增
- event: done  / data: {"conversation_id", "message_id", "model", "title",
                         "message_count", "intent", "sub_intent", "subgraph",
                         "result_status"}（用户停止时 result_status="stopped"）
- event: error / data: {"conversation_id", "message_id", "message"}

非教学子图不调用模型，start/done 中的 model 为 null。
用户消息与 AI 回复均持久化；模型失败、Agent 超时或生成中断时保存
status=error 的助手消息，用户主动停止时保存 status=stopped，
两者都保留已生成部分文本，不得伪造成功回复。

V1.4：卡片一次性完整下发（禁止 card_delta 增量拼接），
未知版本/类型由 app/schemas/cards.py 纯函数降级为 error_card；
卡片数据附属于同一条助手消息，不新增消息行、不改变 message_count 口径。
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent.contracts import AgentRunError
from app.agent.runner import AgentRun, AgentService
from app.db.session import get_db
from app.schemas.cards import normalize_card
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    ConversationTitleUpdate,
    MessageCreate,
    MessageOut,
    RegenerateRequest,
    StopGenerationOut,
)
from app.services.conversation_service import ConversationService
from app.services.generation_registry import generation_registry
from app.services.llm_client import LlmError

logger = logging.getLogger("xiaoma.conversation")

router = APIRouter(prefix="/conversations", tags=["conversations"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # 关闭反向代理缓冲，保证逐段输出
}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _message_out(message) -> MessageOut:
    """把 ORM 消息转成含 V1.4 卡片字段的输出结构。"""
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        status=message.status,
        error_message=message.error_message,
        model_name=message.model_name,
        created_at=message.created_at,
        message_type=message.message_type,
        structured_data=message.structured_data,
        card_version=message.card_version,
    )


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
    """查看会话及其全部持久化消息（用于刷新后继续阅读/恢复卡片）。"""
    return ConversationService(db).get_conversation(conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationDetailOut)
def rename_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationTitleUpdate,
    db: Session = Depends(get_db),
) -> ConversationDetailOut:
    """V1.4：会话重命名（局部更新，只接受 title）。"""
    return ConversationService(db).rename_conversation(
        conversation_id, payload.title
    )


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    """物理删除聊天会话及其全部消息（不可恢复），其他会话不受影响。"""
    ConversationService(db).delete_conversation(conversation_id)
    return Response(status_code=204)


def _stream_reply(run: AgentRun) -> StreamingResponse:
    """把一次 AgentRun 写成 SSE 流，并统一处理成功/失败/停止/断连。"""
    context = run.chat_context
    conversation_id = context.conversation.id
    assistant_id = (
        str(run.assistant_message.id) if run.assistant_message is not None else None
    )
    # 在返回响应前登记，stop 端点可在流开始后立刻命中同一标志
    stop_flag = generation_registry.register(conversation_id)

    def _persist_error(message: str) -> str | None:
        """保存失败回复；持久化自身出错不影响向用户发送错误提示。"""
        try:
            saved = run.fail(message)
            return str(saved.id)
        except Exception:
            logger.exception(
                "保存失败回复时出错: conversation_id=%s", conversation_id
            )
            return None

    def _done_payload(message_id: str | None, result_status: str) -> dict:
        return {
            "conversation_id": str(conversation_id),
            "message_id": message_id,
            "model": run.message_model_name,
            "title": context.conversation.title,
            "message_count": context.learning_session.message_count,
            "result_status": result_status,
        }

    async def event_source() -> AsyncIterator[str]:
        try:
            yield _sse(
                "start",
                {
                    "conversation_id": str(conversation_id),
                    "user_message_id": str(context.user_message.id),
                    "message_id": assistant_id,
                    "model": run.message_model_name,
                    "title": context.conversation.title,
                    "intent": run.intent.intent,
                    "sub_intent": run.intent.sub_intent,
                },
            )
            done_event: dict | None = None
            try:
                async for event in run.astream():
                    if stop_flag.is_set():
                        break
                    if event["event"] == "delta":
                        yield _sse("delta", {"text": event["delta"]})
                    elif event["event"] == "card":
                        # 一次性完整 JSON；不合法帧已被纯函数降级为 error_card
                        card = normalize_card(event["card"])
                        yield _sse(
                            "card",
                            {
                                "conversation_id": str(conversation_id),
                                "message_id": assistant_id,
                                "card_version": card["card_version"],
                                "message_type": card["type"],
                                "structured_data": card,
                            },
                        )
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
                        "conversation_id": str(conversation_id),
                        "message_id": message_id,
                        "message": exc.message,
                    },
                )
                return
            except AgentRunError as exc:
                logger.warning(
                    "Agent 执行失败: conversation_id=%s error=%s",
                    conversation_id,
                    exc.message,
                )
                message_id = _persist_error(exc.message)
                yield _sse(
                    "error",
                    {
                        "conversation_id": str(conversation_id),
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
                    conversation_id,
                )
                message_id = _persist_error("服务器内部错误，请稍后重试")
                yield _sse(
                    "error",
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": message_id,
                        "message": "服务器内部错误，请稍后重试",
                    },
                )
                return

            if stop_flag.is_set():
                # 用户主动停止：落 status=stopped 的部分消息，发 done 但不伪造成功
                stopped = run.stop()
                yield _sse(
                    "done",
                    {
                        **_done_payload(str(stopped.id), "stopped"),
                        "intent": run.intent.intent,
                        "sub_intent": run.intent.sub_intent,
                        "subgraph": None,
                    },
                )
                return

            if done_event is None:
                # 理论上不会发生；仍按失败处理，绝不把不完整结果标记为成功
                message_id = _persist_error("Agent 未返回完成状态")
                yield _sse(
                    "error",
                    {
                        "conversation_id": str(conversation_id),
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
                    "保存 AI 回复失败: conversation_id=%s", conversation_id
                )
                yield _sse(
                    "error",
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": assistant_id,
                        "message": "回复已生成但保存失败，请重试",
                    },
                )
                return
            yield _sse(
                "done",
                {
                    **_done_payload(str(message.id), "ok"),
                    "intent": done_event.get("intent"),
                    "sub_intent": done_event.get("sub_intent"),
                    "subgraph": done_event.get("subgraph"),
                },
            )
        finally:
            generation_registry.unregister(conversation_id, stop_flag)

    return StreamingResponse(
        event_source(), media_type="text/event-stream", headers=SSE_HEADERS
    )


@router.post("/{conversation_id}/messages/stream")
def send_message_stream(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    # 流式生成期间仍需使用数据库会话保存 AI 回复，故依赖随请求生命周期释放
    db: Session = Depends(get_db, scope="request"),
) -> StreamingResponse:
    """发送用户消息，由主 Agent 路由到子图并以 SSE 流式返回回复。"""
    run = AgentService(db).start(conversation_id, payload.content)
    return _stream_reply(run)


@router.post(
    "/{conversation_id}/messages/stop", response_model=StopGenerationOut
)
def stop_generation(
    conversation_id: uuid.UUID, db: Session = Depends(get_db)
) -> StopGenerationOut:
    """V1.4：请求停止当前生成。

    只置位进程内标志，真正落 ``status=stopped`` 的部分消息由 SSE 生成器
    在事件边界完成，避免两个请求同时写同一行。无进行中的生成时返回
    ``stopped=false``（幂等，不报错）。
    """
    ConversationService(db).get_conversation(conversation_id)  # 不存在则 404
    stopped = generation_registry.request_stop(conversation_id)
    return StopGenerationOut(
        conversation_id=conversation_id, stopped=stopped
    )


@router.post(
    "/{conversation_id}/messages/regenerate", response_model=MessageOut
)
async def regenerate_message(
    conversation_id: uuid.UUID,
    payload: RegenerateRequest,
    db: Session = Depends(get_db, scope="request"),
) -> MessageOut:
    """V1.4：重新生成一条普通文本回复（不写新的用户消息）。

    与 SSE 不同，本接口一次性返回新的助手消息；失败先按既有语义落
    status=error，再以 502 明确告知，绝不返回伪造的成功回复。
    """
    run = AgentService(db).start_regenerate(conversation_id, payload.message_id)
    try:
        async for _event in run.astream():
            pass
    except (LlmError, AgentRunError) as exc:
        run.fail(exc.message)
        raise HTTPException(status_code=502, detail=exc.message) from None
    except (asyncio.CancelledError, GeneratorExit):
        run.fail("回复生成已中断")
        raise
    except Exception:
        logger.exception(
            "重新生成失败: conversation_id=%s", conversation_id
        )
        run.fail("服务器内部错误，请稍后重试")
        raise HTTPException(
            status_code=500, detail="服务器内部错误，请稍后重试"
        ) from None
    return _message_out(run.complete())
