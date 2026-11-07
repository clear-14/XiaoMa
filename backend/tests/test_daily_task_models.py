"""每日任务模型测试：关系、唯一约束（防重复机制）、状态约束与级联删除。"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.course import Chapter, Course, KnowledgePoint
from app.models.daily_task import DailyTask
from app.models.learning_plan import LearningPlan, LearningPlanVersion
from app.models.user import User


def _make_task(db_session):
    """创建 用户/课程/知识点/计划/任务 结构，返回 (task, plan, kp)。"""
    user = User(username="task-user")
    course = Course(code="task-course", name="任务测试课程")
    chapter = Chapter(code="task-course-01", title="第一章", order_index=1, course=course)
    kp = KnowledgePoint(
        code="task-course-01-01",
        name="知识点",
        chapter=chapter,
        learning_goal="掌握该知识点",
        difficulty="beginner",
        estimated_minutes=15,
        mastery_criteria="能独立完成练习",
        order_index=1,
    )
    plan = LearningPlan(user=user, course=course, status="active", current_version_number=1)
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
    db_session.add_all([user, course, chapter, kp, plan, version, task])
    return task, plan, kp


def test_task_default_status_pending(db_session):
    task, _, _ = _make_task(db_session)
    db_session.commit()
    assert task.status == "pending"
    assert task.started_at is None
    assert task.completed_at is None
    assert task.task_date == date(2026, 11, 7)


def test_task_knowledge_point_relation(db_session):
    task, _, _ = _make_task(db_session)
    db_session.commit()
    loaded = db_session.scalars(select(DailyTask).where(DailyTask.id == task.id)).one()
    assert loaded.knowledge_point.code == "task-course-01-01"
    assert loaded.plan.course.code == "task-course"


def test_task_unique_per_user_date_and_knowledge_point(db_session):
    task, plan, kp = _make_task(db_session)
    db_session.commit()

    db_session.add(
        DailyTask(
            user_id=task.user_id,
            plan_id=plan.id,
            knowledge_point_id=kp.id,
            task_date=task.task_date,
            day_index=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_task_invalid_status_rejected(db_session):
    task, _, _ = _make_task(db_session)
    task.status = "mastered"
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_plan_delete_cascades_tasks(db_session):
    task, plan, _ = _make_task(db_session)
    db_session.commit()
    db_session.delete(plan)
    db_session.commit()
    assert db_session.scalars(select(DailyTask)).all() == []


def test_knowledge_point_delete_cascades_tasks(db_session):
    task, _, kp = _make_task(db_session)
    db_session.commit()
    db_session.delete(kp)
    db_session.commit()
    assert db_session.scalars(select(DailyTask)).all() == []
