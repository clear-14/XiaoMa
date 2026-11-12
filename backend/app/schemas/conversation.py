"""AI 教学聊天接口 Schema（PRD 5.1 AI 教学助手 / 聊天历史，阶段 8）。

会话级关联（产品决策 2026-11-07）：knowledge_point_code 与 daily_task_id
在创建会话时确定，会话内所有消息共享该上下文；只提供每日任务时自动关联
该任务对应的知识点。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    """新建聊天会话请求。"""

    title: str | None = Field(default=None, max_length=200)
    knowledge_point_code: str | None = Field(default=None, max_length=64)
    daily_task_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        """标题两端空白去除；空字符串视为未命名（使用默认标题）。"""
        if value is None:
            return None
        value = value.strip()
        return value or None


class MessageCreate(BaseModel):
    """发送一条用户消息。"""

    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息内容不能为空")
        return value


class ConversationKnowledgePointOut(BaseModel):
    """会话关联的知识点摘要。"""

    code: str
    name: str
    chapter_code: str
    chapter_title: str


class MessageOut(BaseModel):
    """一条历史消息。

    status=error / stopped 表示该 AI 回复生成失败或被用户停止：content 为
    已生成的部分内容，前端必须显示为失败/已停止，不能当作完整回复。
    V1.4 三个字段用于卡片刷新恢复：message_type、structured_data、
    card_version；普通文本消息 structured_data / card_version 为 None。
    """

    id: UUID
    role: str  # user | assistant
    content: str
    status: str  # completed | error | streaming | stopped
    error_message: str | None = None
    model_name: str | None = None
    created_at: datetime
    message_type: str = "text"
    structured_data: dict | None = None
    card_version: str | None = None


class ConversationTitleUpdate(BaseModel):
    """会话重命名（PATCH 局部更新，只接受 title）。"""

    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("会话标题不能为空")
        return value


class RegenerateRequest(BaseModel):
    """重新生成：指定一条普通文本助手回复，复用其前置用户消息。"""

    message_id: UUID


class StopGenerationOut(BaseModel):
    """停止生成请求的结果。stopped=False 表示该会话当前没有进行中的生成。"""

    conversation_id: UUID
    stopped: bool


class ConversationOut(BaseModel):
    """会话列表项。"""

    id: UUID
    title: str  # 未命名会话显示「新对话」
    knowledge_point: ConversationKnowledgePointOut | None = None
    daily_task_id: UUID | None = None
    message_count: int
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    """会话详情：包含完整持久化消息历史。"""

    messages: list[MessageOut]
