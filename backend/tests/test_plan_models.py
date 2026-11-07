"""学习计划模型测试：关系、唯一约束与级联删除。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.course import Chapter, Course, KnowledgePoint
from app.models.learning_plan import LearningPlan, LearningPlanItem, LearningPlanVersion
from app.models.user import User


def _make_plan(db_session):
    """创建 用户/课程/知识点/计划/版本 结构，返回 (plan, version, kp)。"""
    user = User(username="plan-user")
    course = Course(code="plan-course", name="计划测试课程")
    chapter = Chapter(code="plan-course-01", title="第一章", order_index=1, course=course)
    kp = KnowledgePoint(
        code="plan-course-01-01",
        name="知识点",
        chapter=chapter,
        learning_goal="掌握该知识点",
        difficulty="beginner",
        estimated_minutes=15,
        mastery_criteria="能独立完成练习",
        order_index=1,
    )
    plan = LearningPlan(user=user, course=course, status="draft", pending_version_number=1)
    version = LearningPlanVersion(
        plan=plan,
        version_number=1,
        status="draft",
        learning_goal="学会 Python",
        daily_study_minutes=30,
        expected_duration_days=60,
        computed_duration_days=10,
    )
    db_session.add_all([user, course, chapter, kp, plan, version])
    return plan, version, kp


def test_plan_version_item_relations(db_session):
    plan, version, kp = _make_plan(db_session)
    item = LearningPlanItem(
        version=version, knowledge_point=kp, day_index=1, status="pending"
    )
    db_session.add(item)
    db_session.commit()

    loaded = db_session.scalars(select(LearningPlan).where(LearningPlan.id == plan.id)).one()
    assert len(loaded.versions) == 1
    assert loaded.versions[0].items[0].knowledge_point.code == "plan-course-01-01"
    assert loaded.versions[0].items[0].status == "pending"


def test_version_number_unique_per_plan(db_session):
    plan, version, _ = _make_plan(db_session)
    db_session.commit()

    db_session.add(
        LearningPlanVersion(
            plan=plan,
            version_number=1,
            status="draft",
            learning_goal="重复版本",
            daily_study_minutes=30,
            expected_duration_days=60,
            computed_duration_days=10,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_item_knowledge_point_unique_per_version(db_session):
    plan, version, kp = _make_plan(db_session)
    db_session.add(
        LearningPlanItem(version=version, knowledge_point=kp, day_index=1)
    )
    db_session.commit()

    db_session.add(
        LearningPlanItem(version=version, knowledge_point=kp, day_index=2)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_plan_delete_cascades_versions_and_items(db_session):
    plan, version, kp = _make_plan(db_session)
    db_session.add(
        LearningPlanItem(version=version, knowledge_point=kp, day_index=1)
    )
    db_session.commit()

    db_session.delete(plan)
    db_session.commit()

    assert db_session.scalars(select(LearningPlanVersion)).all() == []
    assert db_session.scalars(select(LearningPlanItem)).all() == []


def test_item_default_status_pending(db_session):
    plan, version, kp = _make_plan(db_session)
    item = LearningPlanItem(version=version, knowledge_point=kp, day_index=1)
    db_session.add(item)
    db_session.commit()
    assert item.status == "pending"
    assert item.completed_at is None
