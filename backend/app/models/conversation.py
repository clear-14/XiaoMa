"""AI 教学聊天模型：会话、消息与学习会话（PRD 5.1 聊天历史 / PRD 9）。

设计要点：
- 会话（conversations）持久化保存，新建会话永远创建新记录，不覆盖旧会话；
- 会话可关联知识点与每日任务（会话级关联，会话内消息共享上下文）；
- 消息（messages）记录用户与 AI 的完整对话；模型失败时保存 status=error
  的助手消息（保留已生成的部分内容并明确标记失败），不得伪造成功回复；
- 学习会话（learning_sessions）与对话 1:1（产品决策 2026-11-07），记录本次
  学习活动的关联任务/知识点、开始时间、最后活动时间与消息数，供学习记录使用。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin
from app.models.course import KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.user import User

MESSAGE_ROLES: tuple[str, ...] = ("user", "assistant")
MESSAGE_STATUSES: tuple[str, ...] = ("completed", "error")


class Conversation(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """一次 AI 教学对话（可关联知识点与每日任务）。"""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 会话标题：创建时可选；未提供时由第一条用户消息自动生成
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 会话级上下文关联（产品决策 2026-11-07）；知识点/任务删除后置空
    knowledge_point_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="SET NULL"), nullable=True, index=True
    )
    daily_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("daily_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped[User] = relationship()
    knowledge_point: Mapped[KnowledgePoint | None] = relationship()
    daily_task: Mapped[DailyTask | None] = relationship()
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    learning_session: Mapped[LearningSession | None] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Message(UUIDPkMixin, TimestampMixin, Base):
    """会话中的一条消息（用户或 AI）。

    status=error 表示该 AI 回复生成失败/被中断：content 为已生成的部分内容
    （可能为空），error_message 为明确原因；历史中展示为失败，不当作正常回复。
    """

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="role"),
        CheckConstraint("status IN ('completed', 'error')", name="status"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 生成该回复所用模型（便于追溯；不记录密钥）
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class LearningSession(UUIDPkMixin, TimestampMixin, Base):
    """学习会话记录，与对话 1:1（产品决策 2026-11-07）。"""

    __tablename__ = "learning_sessions"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="conversation_session"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="SET NULL"), nullable=True
    )
    daily_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("daily_tasks.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    conversation: Mapped[Conversation] = relationship(back_populates="learning_session")
    user: Mapped[User] = relationship()
    knowledge_point: Mapped[KnowledgePoint | None] = relationship()
    daily_task: Mapped[DailyTask | None] = relationship()
