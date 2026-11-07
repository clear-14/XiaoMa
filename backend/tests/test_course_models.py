"""课程体系与知识点学习档案模型测试。"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.course import Chapter, Course, KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.user import User


def _make_course_kp(db_session, kp_code="test-course-01-01", order_index=1):
    """创建 课程→章节→知识点 结构并返回 (course, chapter, kp)。"""
    course = Course(code="test-course", name="测试课程")
    chapter = Chapter(
        code="test-course-01", title="第一章", order_index=1, course=course
    )
    kp = KnowledgePoint(
        code=kp_code,
        name=f"知识点 {kp_code}",
        chapter=chapter,
        learning_goal="掌握该知识点",
        difficulty="beginner",
        estimated_minutes=15,
        mastery_criteria="能独立完成练习",
        order_index=order_index,
    )
    db_session.add_all([course, chapter, kp])
    return course, chapter, kp


def test_course_chapter_kp_relations_and_order(db_session):
    course, chapter, kp1 = _make_course_kp(db_session)
    kp2 = KnowledgePoint(
        code="test-course-01-02",
        name="知识点 2",
        chapter=chapter,
        learning_goal="掌握该知识点",
        difficulty="beginner",
        estimated_minutes=10,
        mastery_criteria="能独立完成练习",
        order_index=2,
    )
    db_session.add(kp2)
    db_session.commit()

    loaded = db_session.scalars(select(Course).where(Course.code == "test-course")).one()
    assert [c.code for c in loaded.chapters] == ["test-course-01"]
    # 关系按 order_index 排序
    assert [k.code for k in loaded.chapters[0].knowledge_points] == [
        "test-course-01-01",
        "test-course-01-02",
    ]
    assert loaded.chapters[0].knowledge_points[0].chapter is loaded.chapters[0]


def test_prerequisite_self_relation(db_session):
    course, chapter, kp_a = _make_course_kp(db_session, kp_code="test-course-01-01")
    kp_b = KnowledgePoint(
        code="test-course-01-02",
        name="知识点 2",
        chapter=chapter,
        learning_goal="掌握该知识点",
        difficulty="beginner",
        estimated_minutes=10,
        mastery_criteria="能独立完成练习",
        order_index=2,
    )
    kp_b.prerequisites.append(kp_a)
    db_session.add(kp_b)
    db_session.commit()

    loaded = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "test-course-01-02")
    ).one()
    assert [p.code for p in loaded.prerequisites] == ["test-course-01-01"]


def test_chapter_delete_cascades_knowledge_points(db_session):
    _, chapter, kp = _make_course_kp(db_session)
    db_session.commit()
    db_session.delete(chapter)
    db_session.commit()

    remaining = list(
        db_session.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == kp.code)
        ).all()
    )
    assert remaining == []


def test_course_code_unique(db_session):
    db_session.add(Course(code="dup-course", name="课程 A"))
    db_session.commit()
    db_session.add(Course(code="dup-course", name="课程 B"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_knowledge_point_code_unique(db_session):
    _make_course_kp(db_session)
    db_session.commit()
    _, chapter, _ = _make_course_kp(db_session)
    db_session.add(
        KnowledgePoint(
            code="test-course-01-01",
            name="重复知识点",
            chapter=chapter,
            learning_goal="掌握该知识点",
            difficulty="beginner",
            estimated_minutes=10,
            mastery_criteria="能独立完成练习",
            order_index=2,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_learning_profile_unique_per_user_and_kp(db_session):
    user = User(username="u1")
    _, _, kp = _make_course_kp(db_session)
    db_session.add(user)
    db_session.commit()

    db_session.add(
        LearningProfile(user_id=user.id, knowledge_point_id=kp.id, status="learning")
    )
    db_session.commit()

    db_session.add(
        LearningProfile(user_id=user.id, knowledge_point_id=kp.id, status="mastered")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_learning_profile_status_check_constraint(db_session):
    user = User(username="u1")
    _, _, kp = _make_course_kp(db_session)
    db_session.add(user)
    db_session.commit()

    db_session.add(
        LearningProfile(user_id=user.id, knowledge_point_id=kp.id, status="bogus_status")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_learning_profile_default_status(db_session):
    user = User(username="u1")
    _, _, kp = _make_course_kp(db_session)
    db_session.add(user)
    db_session.commit()

    profile = LearningProfile(user_id=user.id, knowledge_point_id=kp.id)
    db_session.add(profile)
    db_session.commit()
    assert profile.status == "not_started"


def test_soft_delete_defaults_and_fields(db_session):
    course, _, kp = _make_course_kp(db_session)
    db_session.commit()
    assert course.deleted_at is None
    assert kp.deleted_at is None
    assert kp.learning_goal and kp.mastery_criteria and kp.estimated_minutes > 0
