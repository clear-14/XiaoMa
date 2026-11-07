"""聊天模型测试：默认值、角色/状态约束、学习会话 1:1、级联删除与关联关系。"""

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.conversation import Conversation, LearningSession, Message
from app.models.course import Chapter, Course, KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanVersion
from app.models.user import User
from app.services.time_utils import utc_now_naive


def _make_conversation(db_session):
    """创建用户/课程/知识点/计划/任务/会话/学习会话完整结构。"""
    user = User(username="conv-user")
    course = Course(code="conv-course", name="聊天测试课程")
    chapter = Chapter(code="conv-course-01", title="第一章", order_index=1, course=course)
    kp = KnowledgePoint(
        code="conv-course-01-01",
        name="变量",
        chapter=chapter,
        learning_goal="理解变量",
        difficulty="beginner",
        estimated_minutes=15,
        mastery_criteria="能定义变量",
        order_index=1,
    )
    plan = LearningPlan(
        user=user, course=course, status="active", current_version_number=1
    )
    version = LearningPlanVersion(
        plan=plan,
        version_number=1,
        status="active",
        learning_goal="学会 Python",
        daily_study_minutes=30,
        expected_duration_days=60,
        computed_duration_days=10,
    )
    task = DailyTask(
        user=user,
        plan=plan,
        knowledge_point=kp,
        task_date=date(2026, 11, 7),
        day_index=1,
    )
    now = utc_now_naive()
    conversation = Conversation(
        user=user, title="测试会话", knowledge_point=kp, daily_task=task
    )
    conversation.learning_session = LearningSession(
        user=user,
        knowledge_point=kp,
        daily_task=task,
        started_at=now,
        last_activity_at=now,
    )
    db_session.add_all([user, course, chapter, kp, plan, version, task, conversation])
    return conversation, user, kp, task


def test_conversation_relations_and_session_defaults(db_session):
    conversation, user, kp, task = _make_conversation(db_session)
    db_session.commit()

    assert conversation.title == "测试会话"
    assert conversation.user_id == user.id
    assert conversation.knowledge_point.code == "conv-course-01-01"
    assert conversation.daily_task.id == task.id
    assert conversation.learning_session is not None
    assert conversation.learning_session.conversation_id == conversation.id
    assert conversation.learning_session.message_count == 0
    assert conversation.learning_session.started_at is not None
    assert conversation.learning_session.last_activity_at is not None


def test_message_defaults_and_order(db_session):
    conversation, _, _, _ = _make_conversation(db_session)
    db_session.commit()
    db_session.add(
        Message(conversation_id=conversation.id, role="user", content="什么是变量？")
    )
    db_session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="变量是保存数据的名字。",
            model_name="test-model",
        )
    )
    db_session.commit()

    messages = list(
        db_session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert [m.role for m in messages] == ["user", "assistant"]
    assert all(m.status == "completed" for m in messages)
    assert messages[1].model_name == "test-model"


def test_message_invalid_role_rejected(db_session):
    conversation, _, _, _ = _make_conversation(db_session)
    db_session.commit()
    db_session.add(
        Message(conversation_id=conversation.id, role="system", content="非法角色")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_message_invalid_status_rejected(db_session):
    conversation, _, _, _ = _make_conversation(db_session)
    db_session.commit()
    db_session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="失败",
            status="success",  # 非法状态
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_learning_session_unique_per_conversation(db_session):
    conversation, user, kp, task = _make_conversation(db_session)
    db_session.commit()
    now = utc_now_naive()
    db_session.add(
        LearningSession(
            conversation_id=conversation.id,
            user_id=user.id,
            knowledge_point_id=kp.id,
            daily_task_id=task.id,
            started_at=now,
            last_activity_at=now,
            message_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_delete_conversation_cascades_messages_and_session(db_session):
    conversation, _, _, _ = _make_conversation(db_session)
    db_session.commit()
    db_session.add(
        Message(conversation_id=conversation.id, role="user", content="你好")
    )
    db_session.commit()
    conversation_id = conversation.id

    db_session.delete(conversation)
    db_session.commit()

    assert (
        db_session.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id
            )
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count(LearningSession.id)).where(
                LearningSession.conversation_id == conversation_id
            )
        )
        == 0
    )
