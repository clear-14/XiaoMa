"""排期算法与计划结构校验测试（后端权威规则）。"""

import pytest

from app.models.course import Chapter, Course, KnowledgePoint
from app.seed.course_seed import seed_courses
from app.services.plan_scheduler import (
    build_schedule,
    computed_duration_days,
    validate_schedule,
)


def _kp(code, minutes=20, chapter_index=1, kp_index=1):
    chapter = Chapter(
        code=f"test-{chapter_index}", title="章", order_index=chapter_index, course=Course(code="test", name="测试")
    )
    return KnowledgePoint(
        code=code,
        name=code,
        chapter=chapter,
        learning_goal="g",
        difficulty="beginner",
        estimated_minutes=minutes,
        mastery_criteria="c",
        order_index=kp_index,
    )


def test_build_schedule_packs_days_by_daily_minutes():
    kps = [_kp("kp-1", 20), _kp("kp-2", 20), _kp("kp-3", 20), _kp("kp-4", 10)]
    schedule = build_schedule(kps, set(), 30)
    # 20+20>30 → kp-1 第1天；kp-2 第2天；kp-2(20)+kp-3(20)>30 → kp-3 第3天；kp-3(20)+kp-4(10)=30 → kp-4 第3天
    assert [day for _, day in schedule] == [1, 2, 3, 3]
    assert computed_duration_days(schedule) == 3


def test_build_schedule_excludes_mastered():
    kps = [_kp("kp-1", 20), _kp("kp-2", 20), _kp("kp-3", 20)]
    schedule = build_schedule(kps, {"kp-2"}, 30)
    assert [kp.code for kp, _ in schedule] == ["kp-1", "kp-3"]


def test_build_schedule_oversized_kp_occupies_day_alone():
    kps = [_kp("kp-1", 60), _kp("kp-2", 20)]
    schedule = build_schedule(kps, set(), 30)
    # 60 分钟知识点不拆分，独自占满第 1 天
    assert [(kp.code, day) for kp, day in schedule] == [("kp-1", 1), ("kp-2", 2)]


def test_build_schedule_empty_when_all_mastered():
    kps = [_kp("kp-1", 20)]
    schedule = build_schedule(kps, {"kp-1"}, 30)
    assert schedule == []
    assert computed_duration_days(schedule) == 0


def test_validate_schedule_accepts_valid_structure():
    a, b, c = _kp("kp-a", 20), _kp("kp-b", 20), _kp("kp-c", 20)
    b.prerequisites.append(a)
    c.prerequisites.append(a)
    schedule = [(a, 1), (b, 2), (c, 2)]
    # 不抛异常即通过
    validate_schedule(
        schedule, {kp.code: kp for kp in (a, b, c)}, set(),
        {"kp-a": 0, "kp-b": 1, "kp-c": 2},
    )


def test_validate_schedule_prereq_not_in_course():
    a = _kp("kp-a", 20)
    schedule = [(a, 1)]
    with pytest.raises(ValueError, match="不属于该课程"):
        validate_schedule(schedule, {}, set(), {"kp-a": 0})


def test_validate_schedule_duplicate_kp():
    a = _kp("kp-a", 20)
    with pytest.raises(ValueError, match="重复安排"):
        validate_schedule(
            [(a, 1), (a, 2)], {"kp-a": a}, set(), {"kp-a": 0}
        )


def test_validate_schedule_prereq_later_day_rejected():
    a, b = _kp("kp-a", 20), _kp("kp-b", 20)
    b.prerequisites.append(a)
    with pytest.raises(ValueError, match="前置知识点 kp-a"):
        validate_schedule(
            [(b, 1), (a, 2)], {"kp-a": a, "kp-b": b}, set(),
            {"kp-a": 0, "kp-b": 1},
        )


def test_validate_schedule_prereq_same_day_but_later_in_course_rejected():
    a, b = _kp("kp-a", 20), _kp("kp-b", 20)
    b.prerequisites.append(a)
    # 同一天但前置知识点在课程顺序上更靠后 → 拒绝
    with pytest.raises(ValueError, match="课程顺序"):
        validate_schedule(
            [(a, 1), (b, 1)], {"kp-a": a, "kp-b": b}, set(),
            {"kp-a": 1, "kp-b": 0},
        )


def test_validate_schedule_mastered_prereq_not_required():
    a, b = _kp("kp-a", 20), _kp("kp-b", 20)
    b.prerequisites.append(a)
    # 前置已掌握 → 无需安排在前
    validate_schedule(
        [(b, 1)], {"kp-a": a, "kp-b": b}, {"kp-a"}, {"kp-a": 0, "kp-b": 1}
    )


def test_validate_schedule_missing_prereq_rejected():
    a, b = _kp("kp-a", 20), _kp("kp-b", 20)
    b.prerequisites.append(a)
    with pytest.raises(ValueError, match="未安排在计划中"):
        validate_schedule(
            [(b, 1)], {"kp-a": a, "kp-b": b}, set(), {"kp-a": 0, "kp-b": 1}
        )


def test_generated_seed_schedule_satisfies_prerequisites(db_session):
    """用真实种子课程验证：排期算法产出的计划天然满足全部前置依赖。"""
    seed_courses(db_session)
    from app.repositories.course_repository import CourseRepository

    kps = CourseRepository(db_session).get_course_knowledge_points("python-basics")
    mastered = {"python-basics-01-02"}
    schedule = build_schedule(kps, mastered, 45)
    order_position = {kp.code: i for i, kp in enumerate(kps)}
    # 不抛异常即通过
    validate_schedule(
        schedule, {kp.code: kp for kp in kps}, mastered, order_position
    )
    # 排期顺序与课程顺序一致（前置先于依赖）
    days = {kp.code: day for kp, day in schedule}
    for kp, day in schedule:
        for prereq in kp.prerequisites:
            if prereq.code in mastered:
                continue
            assert days[prereq.code] <= day
