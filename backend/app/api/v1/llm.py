"""统一 LLM 接口：流式对话（SSE）。

事件格式：
- event: start / data: {"model": "..."}
- event: delta / data: {"text": "增量文本"}
- event: done  / data: {"model": "..."}
- event: error / data: {"message": "明确的中文错误提示"}

配置问题（无默认模型、密钥无法解密）在开始流式响应前以 HTTP 错误返回；
服务商在流式过程中出错时通过 error 事件明确提示（PRD 7.3）。
"""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.llm import ChatStreamRequest
from app.services.llm_client import LlmError
from app.services.model_config_service import ModelConfigService

logger = logging.getLogger("xiaoma.llm")

router = APIRouter(prefix="/llm", tags=["llm"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # 关闭反向代理缓冲，保证逐段输出
}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(
    payload: ChatStreamRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    """流式对话：使用默认模型（或指定 config_id）逐段输出回复。"""
    service = ModelConfigService(db)
    llm_request, messages = service.prepare_chat_stream(
        payload.config_id, [message.model_dump() for message in payload.messages]
    )
    stream = service.stream_chat(llm_request, messages)

    async def event_source() -> AsyncIterator[str]:
        yield _sse("start", {"model": llm_request.model_name})
        try:
            async for delta in stream:
                yield _sse("delta", {"text": delta})
            yield _sse("done", {"model": llm_request.model_name})
        except LlmError as exc:
            logger.warning("模型流式调用失败: provider=%s model=%s error=%s",
                           llm_request.provider, llm_request.model_name, exc.message)
            yield _sse("error", {"message": exc.message})
        except Exception:
            logger.exception("模型流式调用未处理异常: provider=%s model=%s",
                             llm_request.provider, llm_request.model_name)
            yield _sse("error", {"message": "服务器内部错误，请稍后重试"})

    return StreamingResponse(
        event_source(), media_type="text/event-stream", headers=SSE_HEADERS
    )
