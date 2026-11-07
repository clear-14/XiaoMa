"""AI 教学对话业务层（PRD 5.1 AI 教学助手 / 聊天历史，阶段 8）。

职责与规则：
- 新建、查询、继续、删除聊天会话；新建会话永远创建新记录，不覆盖旧会话；
- 删除会话为物理删除：会话、消息与学习会话记录一并移除，删除后不可恢复；
- 会话级关联知识点与每日任务（产品决策 2026-11-07），会话内消息共享上下文；
- 每次对话从数据库读取学习者档案、知识点、任务与掌握状态，构建教学提示词；
- 用户消息与 AI 回复全部持久化；模型失败/中断时保存 status=error 的助手消息，
  保留已生成的部分文本并记录明确原因，绝不伪造成功回复；
- 学习会话（learning_sessions）与对话 1:1，记录开始时间、最后活动时间与消息数；
- 事务与数据写入均在 Service 层完成，Agent 不直接操作数据库。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, LearningSession, Message
from app.models.course import KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.daily_task_repository import DailyTaskRepository
from app.repositories.learning_profile_repository import LearningProfileRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationKnowledgePointOut,
    ConversationOut,
    MessageOut,
)
from app.services.llm_client import LlmRequest
from app.services.model_config_service import ModelConfigService
from app.services.profile_service import DEFAULT_USERNAME
from app.services.teaching_prompt import build_teaching_prompt
from app.services.time_utils import utc_now_naive

DEFAULT_TITLE = "新对话"
AUTO_TITLE_MAX_LENGTH = 24
# 传给模型的最近消息条数（含本轮用户消息）；失败回复不进入上下文
CONTEXT_MESSAGE_LIMIT = 20
# 多取一部分，过滤失败回复后仍能凑够上下文条数
CONTEXT_FETCH_LIMIT = 40
ERROR_MESSAGE_MAX_LENGTH = 500
# 区分「未显式指定 model_name」与「显式指定为 None（非教学子图）」
_MODEL_NAME_FROM_CONTEXT = object()


@dataclass
class ChatContext:
    """一次 Agent 请求所需的上下文（模型参数、提示词与持久化对象）。

    非教学意图不需要模型，llm_request/model_name 允许为 None；
    教学意图在 prepare_chat 阶段就必须取得可用模型，否则直接报错。
    """

    conversation: Conversation
    learning_session: LearningSession
    user_message: Message
    llm_request: LlmRequest | None
    model_name: str | None
    system_prompt: str
    messages: list[dict[str, str]]
    learning_status: str


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ConversationRepository(db)
        self.course_repo = CourseRepository(db)
        self.task_repo = DailyTaskRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.learning_profile_repo = LearningProfileRepository(db)
        self.model_config_service = ModelConfigService(db)

    # ------------------------------------------------------------- 新建会话

    def create_conversation(self, payload: ConversationCreate) -> ConversationDetailOut:
        """新建聊天会话，并同步创建 1:1 学习会话记录。"""
        user = self._get_or_create_user()
        knowledge_point = self._resolve_knowledge_point(payload.knowledge_point_code)
        daily_task = self._resolve_task(payload.daily_task_id, user.id)
        if (
            daily_task is not None
            and knowledge_point is not None
            and daily_task.knowledge_point_id != knowledge_point.id
        ):
            raise HTTPException(status_code=422, detail="每日任务与知识点不匹配")
        # 只传每日任务时，自动关联该任务的知识点
        if knowledge_point is None and daily_task is not None:
            knowledge_point = daily_task.knowledge_point

        now = utc_now_naive()
        conversation = Conversation(
            user_id=user.id,
            title=payload.title,
            knowledge_point=knowledge_point,
            daily_task=daily_task,
        )
        conversation.learning_session = LearningSession(
            user_id=user.id,
            knowledge_point=knowledge_point,
            daily_task=daily_task,
            started_at=now,
            last_activity_at=now,
            message_count=0,
        )
        self.repo.add_conversation(conversation)
        self.db.commit()
        return self._detail_out(conversation, messages=[])

    # ------------------------------------------------------------- 查询历史

    def list_conversations(self) -> list[ConversationOut]:
        """当前用户全部未删除会话，最近活动在前。"""
        user = self._get_or_create_user()
        return [
            self._base_out(conversation)
            for conversation in self.repo.list_conversations(user.id)
        ]

    def get_conversation(self, conversation_id: uuid.UUID) -> ConversationDetailOut:
        """查看会话详情与完整持久化消息历史（刷新页面后可继续阅读）。"""
        conversation = self._get_or_404(conversation_id)
        messages = self.repo.get_messages(conversation.id)
        return self._detail_out(conversation, messages=messages)

    # ------------------------------------------------------------- 删除会话

    def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        """物理删除会话及其消息、学习会话；其他会话不受影响，删除后不可恢复。"""
        conversation = self._get_or_404(conversation_id)
        self.db.delete(conversation)
        self.db.commit()

    # ------------------------------------------------------------- 发送消息

    def prepare_chat(
        self,
        conversation_id: uuid.UUID,
        content: str,
        *,
        require_llm: bool = True,
    ) -> ChatContext:
        """校验上下文，保存用户消息，构造本轮 Agent 请求。

        require_llm=True（教学意图）时，模型未配置/密钥不可解密属于可预期的
        配置问题：在开始流式响应之前以 HTTP 错误明确返回，不保存用户消息。
        非教学意图只查业务数据，不要求模型可用。
        """
        conversation = self._get_or_404(conversation_id)
        llm_request: LlmRequest | None = None
        model_name: str | None = None
        if require_llm:
            llm_request, model_name = self.model_config_service.get_default_llm_request()

        user = conversation.user
        if user is None:
            raise HTTPException(status_code=409, detail="学习档案不存在，请先初始化学习档案")

        learning_session = conversation.learning_session
        now = utc_now_naive()
        if learning_session is None:
            # 数据完整性兜底：历史数据缺少学习会话时补建（正常流程在创建会话时生成）
            learning_session = LearningSession(
                conversation=conversation,
                user_id=conversation.user_id,
                knowledge_point_id=conversation.knowledge_point_id,
                daily_task_id=conversation.daily_task_id,
                started_at=conversation.created_at or now,
                last_activity_at=now,
                message_count=0,
            )
            self.db.add(learning_session)

        if conversation.title is None:
            conversation.title = _auto_title(content)

        knowledge_point = conversation.knowledge_point
        learning_status = "not_started"
        if knowledge_point is not None:
            profile = self.learning_profile_repo.get_profile(user.id, knowledge_point.id)
            if profile is not None:
                learning_status = profile.status

        system_prompt = build_teaching_prompt(
            user, knowledge_point, conversation.daily_task, learning_status
        )

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=content,
            status="completed",
        )
        self.repo.add_message(user_message)
        conversation.updated_at = now
        learning_session.message_count += 1
        learning_session.last_activity_at = now
        self.db.commit()

        recent = self.repo.get_messages(conversation.id, limit=CONTEXT_FETCH_LIMIT)
        context_messages = [
            message for message in recent if _is_context_message(message)
        ][-CONTEXT_MESSAGE_LIMIT:]
        return ChatContext(
            conversation=conversation,
            learning_session=learning_session,
            user_message=user_message,
            llm_request=llm_request,
            model_name=model_name,
            system_prompt=system_prompt,
            messages=[
                {"role": message.role, "content": message.content}
                for message in context_messages
            ],
            learning_status=learning_status,
        )

    # ------------------------------------------------------- AI 回复持久化

    def complete_assistant_message(
        self,
        context: ChatContext,
        content: str,
        *,
        model_name: str | None | object = _MODEL_NAME_FROM_CONTEXT,
    ) -> Message:
        """保存成功的 AI 回复（status=completed）。

        非教学子图不调用模型，显式传 model_name=None，避免把数据查询回答
        误标为由某个模型生成。
        """
        return self._record_assistant_message(
            context,
            content=content,
            status="completed",
            error_message=None,
            model_name=model_name,
        )

    def fail_assistant_message(
        self,
        context: ChatContext,
        partial_content: str,
        error_message: str,
        *,
        model_name: str | None | object = _MODEL_NAME_FROM_CONTEXT,
    ) -> Message:
        """保存失败的 AI 回复：保留已生成部分文本并明确标记失败（不伪造回复）。"""
        return self._record_assistant_message(
            context,
            content=partial_content or "",
            status="error",
            error_message=error_message[:ERROR_MESSAGE_MAX_LENGTH],
            model_name=model_name,
        )

    def _record_assistant_message(
        self,
        context: ChatContext,
        *,
        content: str,
        status: str,
        error_message: str | None,
        model_name: str | None | object,
    ) -> Message:
        now = utc_now_naive()
        resolved_model_name = (
            context.model_name
            if model_name is _MODEL_NAME_FROM_CONTEXT
            else model_name
        )
        message = Message(
            conversation_id=context.conversation.id,
            role="assistant",
            content=content,
            status=status,
            error_message=error_message,
            model_name=resolved_model_name,
        )
        self.repo.add_message(message)
        # message 的新增不会触发 conversation 的 onupdate，显式刷新活动时间，
        # 保证会话列表按最近活动排序
        context.conversation.updated_at = now
        context.learning_session.message_count += 1
        context.learning_session.last_activity_at = now
        self.db.commit()
        return message

    # ------------------------------------------------------------- 内部工具

    def _get_or_create_user(self) -> User:
        user = self.profile_repo.get_user_with_profile(DEFAULT_USERNAME)
        if user is None:
            user = self.profile_repo.create_user_with_profile(DEFAULT_USERNAME)
            self.db.commit()
        return user

    def _get_or_404(self, conversation_id: uuid.UUID) -> Conversation:
        user = self._get_or_create_user()
        conversation = self.repo.get_conversation(conversation_id, user.id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="聊天会话不存在")
        return conversation

    def _resolve_knowledge_point(self, code: str | None) -> KnowledgePoint | None:
        if not code:
            return None
        knowledge_point = self.course_repo.get_knowledge_point_by_code(code)
        if knowledge_point is None:
            raise HTTPException(status_code=404, detail="知识点不存在")
        return knowledge_point

    def _resolve_task(
        self, task_id: uuid.UUID | None, user_id: uuid.UUID
    ) -> DailyTask | None:
        if task_id is None:
            return None
        task = self.task_repo.get_task(task_id, user_id)
        if task is None:
            raise HTTPException(status_code=404, detail="每日任务不存在")
        return task

    @classmethod
    def _base_out(cls, conversation: Conversation) -> ConversationOut:
        knowledge_point = conversation.knowledge_point
        learning_session = conversation.learning_session
        return ConversationOut(
            id=conversation.id,
            title=conversation.title or DEFAULT_TITLE,
            knowledge_point=(
                ConversationKnowledgePointOut(
                    code=knowledge_point.code,
                    name=knowledge_point.name,
                    chapter_code=knowledge_point.chapter.code,
                    chapter_title=knowledge_point.chapter.title,
                )
                if knowledge_point is not None
                else None
            ),
            daily_task_id=conversation.daily_task_id,
            message_count=learning_session.message_count if learning_session else 0,
            last_activity_at=(
                learning_session.last_activity_at
                if learning_session
                else conversation.created_at
            ),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @classmethod
    def _detail_out(
        cls, conversation: Conversation, messages: list[Message]
    ) -> ConversationDetailOut:
        base = cls._base_out(conversation)
        return ConversationDetailOut(
            **base.model_dump(),
            messages=[cls._message_out(message) for message in messages],
        )

    @staticmethod
    def _message_out(message: Message) -> MessageOut:
        return MessageOut(
            id=message.id,
            role=message.role,
            content=message.content,
            status=message.status,
            error_message=message.error_message,
            model_name=message.model_name,
            created_at=message.created_at,
        )


def _auto_title(content: str) -> str:
    """用第一条用户消息生成会话标题（取首行，超长截断）。"""
    first_line = content.strip().splitlines()[0].strip()
    if len(first_line) <= AUTO_TITLE_MAX_LENGTH:
        return first_line
    return first_line[:AUTO_TITLE_MAX_LENGTH] + "…"


def _is_context_message(message: Message) -> bool:
    """失败/为空的回复不进入模型上下文，避免把未完成输出当作事实。"""
    if not message.content.strip():
        return False
    if message.role == "assistant" and message.status != "completed":
        return False
    return True
