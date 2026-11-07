"""统一 LLM 接口 Schema（流式对话，供模型验证与后续 AI 教学复用）。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatStreamRequest(BaseModel):
    """流式对话请求。config_id 为空时使用默认模型配置。"""

    config_id: UUID | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
