"""聊天会话与消息数据访问层。

会话查询统一过滤软删除；消息按创建顺序返回（持久化历史）。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message
from app.models.course import KnowledgePoint
from app.models.user import User


class ConversationRepository:
    """conversations / messages 的数据库读写。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _conversation_options():
        """会话输出与教学上下文所需关系预取：知识点（含章节）、任务、用户档案、学习会话。"""
        return (
            selectinload(Conversation.knowledge_point).selectinload(
                KnowledgePoint.chapter
            ),
            selectinload(Conversation.daily_task),
            selectinload(Conversation.user).selectinload(User.profile),
            selectinload(Conversation.learning_session),
        )

    def list_conversations(self, user_id: uuid.UUID) -> list[Conversation]:
        """用户全部未删除会话，最近活动在前。"""
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            .options(*self._conversation_options())
        )
        return list(self.db.scalars(stmt).all())

    def get_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        """按 ID 与用户查未删除会话（含教学上下文关系）。"""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .options(*self._conversation_options())
        )
        return self.db.scalars(stmt).first()

    def get_messages(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[Message]:
        """会话消息，按创建时间升序。

        limit 表示只取最近 N 条（用于构造模型上下文），返回结果仍为升序。
        """
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if limit is None:
            stmt = stmt.order_by(Message.created_at.asc())
            return list(self.db.scalars(stmt).all())
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        return list(reversed(list(self.db.scalars(stmt).all())))

    def add_conversation(self, conversation: Conversation) -> None:
        self.db.add(conversation)

    def add_message(self, message: Message) -> None:
        self.db.add(message)
