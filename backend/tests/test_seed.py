"""课程种子数据测试：幂等性、内容恢复与前置关系。"""

from sqlalchemy import func, select

from app.models.course import (
    Chapter,
    Course,
    KnowledgePoint,
    KnowledgePointPrerequisite,
    Lesson,
)
from app.seed.course_seed import SEED_COURSE, seed_courses

EXPECTED_CHAPTERS = 6
EXPECTED_KPS = 31
# 阶段 2 课时目录：6 章拆成 14 个课时
EXPECTED_LESSONS = 14


def _expected_prereq_count() -> int:
    """种子数据中定义的前置关系总数（作为断言基准，避免写死常量漂移）。"""
    return sum(
        len(kp.get("prerequisites", []))
        for ch in SEED_COURSE["chapters"]
        for kp in ch["knowledge_points"]
    )


def test_seed_twice_no_duplicates(db_session):
    first = seed_courses(db_session)
    second = seed_courses(db_session)

    assert first["courses"] == second["courses"] == 1
    assert first["chapters"] == second["chapters"] == EXPECTED_CHAPTERS
    assert first["lessons"] == second["lessons"] == EXPECTED_LESSONS
    assert first["knowledge_points"] == second["knowledge_points"] == EXPECTED_KPS
    # 第二次执行不应新增任何前置关系
    assert second["prerequisites"] == 0
    assert db_session.scalar(select(func.count()).select_from(Course)) == 1
    assert db_session.scalar(select(func.count()).select_from(Chapter)) == EXPECTED_CHAPTERS
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == EXPECTED_LESSONS
    assert db_session.scalar(select(func.count()).select_from(KnowledgePoint)) == EXPECTED_KPS
    assert (
        db_session.scalar(select(func.count()).select_from(KnowledgePointPrerequisite))
        == _expected_prereq_count()
    )


def test_seed_restores_seed_content_without_duplicating(db_session):
    seed_courses(db_session)
    kp = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-01")
    ).one()
    kp.name = "被人工修改过的名称"
    db_session.commit()

    seed_courses(db_session)

    kps = list(
        db_session.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-01")
        ).all()
    )
    assert len(kps) == 1
    assert kps[0].name == SEED_COURSE["chapters"][0]["knowledge_points"][0]["name"]


def test_prerequisite_relations_resolved_by_code(db_session):
    seed_courses(db_session)

    kp = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-04-05")
    ).one()
    assert sorted(p.code for p in kp.prerequisites) == [
        "python-basics-04-03",
        "python-basics-04-04",
    ]

    # 无前置依赖的知识点
    kp_first = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-01")
    ).one()
    assert list(kp_first.prerequisites) == []


def test_prerequisite_relations_cleaned_on_rerun(db_session):
    seed_courses(db_session)
    kp = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-04-05")
    ).one()
    extra = db_session.scalars(
        select(KnowledgePoint).where(KnowledgePoint.code == "python-basics-01-01")
    ).one()
    kp.prerequisites.append(extra)
    db_session.commit()

    seed_courses(db_session)

    # 重新执行后：手工添加的多余前置关系被清除，总数回到种子定义值
    assert sorted(p.code for p in kp.prerequisites) == [
        "python-basics-04-03",
        "python-basics-04-04",
    ]
    assert (
        db_session.scalar(select(func.count()).select_from(KnowledgePointPrerequisite))
        == _expected_prereq_count()
    )


def test_seed_course_content_complete(db_session):
    seed_courses(db_session)

    course = db_session.scalars(
        select(Course).where(Course.code == "python-basics")
    ).one()
    assert course.name == "Python 零基础入门"
    assert course.description

    # 每个知识点必备字段完整且无空值
    kps = list(db_session.scalars(select(KnowledgePoint)).all())
    assert len(kps) == EXPECTED_KPS
    for kp in kps:
        assert kp.name and kp.learning_goal and kp.mastery_criteria
        assert kp.difficulty in {"beginner", "intermediate", "advanced"}
        assert kp.estimated_minutes > 0
        assert kp.order_index >= 1

    # 章节顺序与知识点顺序正确
    course_stored = db_session.scalars(
        select(Course).where(Course.code == "python-basics")
    ).one()
    assert [c.code for c in course_stored.chapters] == [
        f"python-basics-0{i}" for i in range(1, 7)
    ]


def test_lesson_catalog_covers_every_knowledge_point(db_session):
    """阶段 2：6 章拆成 14 个课时，31 个知识点全部有唯一归属。"""
    seed_courses(db_session)

    lessons = list(db_session.scalars(select(Lesson).order_by(Lesson.code)).all())
    assert len(lessons) == EXPECTED_LESSONS
    # 每章首个课时沿用阶段 1 迁移生成的默认课时 code，升级不产生重复课时
    assert lessons[0].code == "python-basics-01-lesson-01"

    total_linked = 0
    for lesson in lessons:
        # 课时预计时长由所属知识点汇总，不单独手填
        assert lesson.estimated_minutes == sum(
            kp.estimated_minutes for kp in lesson.knowledge_points
        )
        assert lesson.estimated_minutes > 0
        total_linked += len(lesson.knowledge_points)
    assert total_linked == EXPECTED_KPS

    kps = list(db_session.scalars(select(KnowledgePoint)).all())
    assert {kp.lesson.code for kp in kps} <= {lesson.code for lesson in lessons}
    assert all(kp.lesson is not None for kp in kps)
