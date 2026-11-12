"""阶段 3 教材测试：Python 零基础入门（20 章完整教材）。

覆盖需求里的 10 项内容验收：
1. 20 个章节存在，code 与顺序连续；
2. 每个章节都有课时，课时信息完整；
3. 每节课的 15 个内容模块都有真实内容；
4. 示例代码、示例输出与逐行解释完整；
5. 通俗解释面向初学者（长度、独立性）；
6. 练习关联知识点并带参考答案；
7. 每节 ≥2 基础理解 + 2 代码阅读 + 2 应用练习，课程覆盖 6 种题型；
8. 不提前使用未学习的语法（按章节顺序）；
9. 课时与题目没有大量重复；
10. 学习计划可以引用课时知识点。

另外覆盖：种子幂等、存量知识点/题库不丢失、内容状态流转、教材接口、
新增 category 列的迁移与回填。
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    Exercise,
    KnowledgePoint,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.quiz import Question
from app.seed.course_catalog_seed import seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.question_seed import seed_questions
from app.seed.textbook import TEXTBOOK, total_exercises, total_questions
from app.seed.textbook_seed import seed_textbook
from app.services.textbook_service import CONTENT_FIELDS, TextbookService

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_CHAPTERS = 20
EXPECTED_LESSONS = 29
EXPECTED_TEXTBOOK_QUESTIONS = 194
EXPECTED_TEXTBOOK_EXERCISES = 58
EXPECTED_LEGACY_KPS = 31
EXPECTED_LEGACY_QUESTIONS = 93
CHAPTER_CODES = [f"python-basics-{index:02d}" for index in range(1, 21)]

# 需求要求支持的六种题型
REQUIRED_TYPES = {
    "single_choice",
    "multiple_choice",
    "true_false",
    "code_analysis",
    "code_writing",
    "short_answer",
}


def _seed(db_session) -> None:
    """按 CLI 顺序写入：课程 → 目录 → 题库 → 教材。"""
    seed_courses(db_session)
    seed_course_catalog(db_session)
    seed_questions(db_session)
    seed_textbook(db_session)


def _course(db):
    return db.scalars(select(Course).where(Course.code == "python-basics")).one()


def _chapters(db) -> list[Chapter]:
    course = _course(db)
    return sorted(
        db.scalars(select(Chapter).where(Chapter.course_id == course.id)).all(),
        key=lambda item: item.order_index,
    )


def _lessons(db) -> list[Lesson]:
    course = _course(db)
    return sorted(
        db.scalars(
            select(Lesson).join(Chapter).where(Chapter.course_id == course.id)
        ).all(),
        key=lambda item: (item.chapter.order_index, item.order_index),
    )


def _lesson_by_code(db, code: str) -> Lesson:
    return db.scalars(select(Lesson).where(Lesson.code == code)).one()


def _questions_of(db, lesson: Lesson) -> list[Question]:
    kp_ids = [kp.id for kp in lesson.knowledge_points]
    if not kp_ids:
        return []
    return list(
        db.scalars(
            select(Question).where(Question.knowledge_point_id.in_(kp_ids))
        ).all()
    )


def _exercises_of(db, lesson: Lesson) -> list[Exercise]:
    kp_ids = [kp.id for kp in lesson.knowledge_points]
    if not kp_ids:
        return []
    return list(
        db.scalars(
            select(Exercise).where(Exercise.knowledge_point_id.in_(kp_ids))
        ).all()
    )


# ---------------------------------------------------------------------------
# 1. 章节与课时结构
# ---------------------------------------------------------------------------


def test_twenty_chapters_exist_in_order(db_session):
    _seed(db_session)

    chapters = _chapters(db_session)
    assert len(chapters) == EXPECTED_CHAPTERS
    assert [chapter.code for chapter in chapters] == CHAPTER_CODES
    assert [chapter.order_index for chapter in chapters] == list(
        range(1, EXPECTED_CHAPTERS + 1)
    )
    # 每章都有标题与简介，不是空壳目录
    for chapter in chapters:
        assert chapter.title.strip()
        assert (chapter.description or "").strip()


def test_every_chapter_has_lessons_with_metadata(db_session):
    _seed(db_session)

    lessons = _lessons(db_session)
    assert len(lessons) == EXPECTED_LESSONS
    for chapter in _chapters(db_session):
        assert chapter.lessons, f"{chapter.code} 没有课时"
    for lesson in lessons:
        assert lesson.title.strip()
        assert lesson.description.strip()
        assert lesson.estimated_minutes and lesson.estimated_minutes > 0
        assert lesson.difficulty in {"beginner", "intermediate", "advanced"}
        assert lesson.knowledge_points, f"{lesson.code} 没有知识点"


def test_lesson_codes_and_knowledge_points_are_linked(db_session):
    _seed(db_session)

    # 课时 code 形如 python-basics-12-l01，知识点 code 全局唯一
    for lesson in _lessons(db_session):
        assert lesson.code.startswith("python-basics-")
        assert "-l" in lesson.code
    kp_codes = [
        kp.code for kp in db_session.scalars(select(KnowledgePoint)).all()
    ]
    assert len(kp_codes) == len(set(kp_codes))
    # 课时与知识点是多对多归属，链接表里每个课时至少一条
    links = db_session.scalars(select(LessonKnowledgePoint)).all()
    assert len(links) >= EXPECTED_LESSONS


# ---------------------------------------------------------------------------
# 2. 15 个内容模块
# ---------------------------------------------------------------------------


def test_every_lesson_has_all_fifteen_modules(db_session):
    _seed(db_session)

    assert len(CONTENT_FIELDS) == 15
    # 示例输出可能只有几行结果，用较低的下限；其余模块要求有实质段落
    minimum_length = {"example_output": 5}
    for lesson in _lessons(db_session):
        content = lesson.content
        assert content is not None, f"{lesson.code} 没有教学内容"
        # 未完成内容不得伪装成已发布
        assert content.status in {"draft", "reviewed", "published"}
        for field, label in CONTENT_FIELDS:
            value = (getattr(content, field) or "").strip()
            assert value, f"{lesson.code} 的「{label}」为空"
            # 模块要有实质内容，不是「略」「TODO」这类占位
            assert len(value) >= minimum_length.get(field, 20), (
                f"{lesson.code} 的「{label}」过短"
            )


def test_example_code_output_and_line_explanations(db_session):
    _seed(db_session)

    for lesson in _lessons(db_session):
        content = lesson.content
        code = content.example_code or ""
        assert code.strip(), f"{lesson.code} 没有示例代码"
        assert code.count("\n") >= 2, f"{lesson.code} 示例代码过短"
        # 每节示例都必须能直接打印出示例输出
        assert "print" in code, f"{lesson.code} 示例代码没有输出语句"
        assert (content.example_output or "").strip(), f"{lesson.code} 没有示例输出"
        lines = [
            line for line in (content.code_explanation or "").splitlines() if line.strip()
        ]
        assert len(lines) >= 3, f"{lesson.code} 逐行解释不足 3 条"


def test_plain_explanation_is_beginner_friendly(db_session):
    _seed(db_session)

    for lesson in _lessons(db_session):
        content = lesson.content
        plain = (content.plain_explanation or "").strip()
        assert len(plain) >= 60, f"{lesson.code} 通俗解释过短"
        # 通俗解释不能是核心概念的复制
        assert plain != (content.concept_explanation or "").strip()
        # 不能是纯代码块
        assert "```" not in plain


# ---------------------------------------------------------------------------
# 3. 抽检重点课时：函数 / 字典 / 循环 / 异常处理
# ---------------------------------------------------------------------------

SPOT_CHECK_LESSONS = [
    "python-basics-08-l01",  # 字典
    "python-basics-10-l01",  # for 循环
    "python-basics-12-l01",  # 函数
    "python-basics-18-l01",  # 异常处理
]


@pytest.mark.parametrize("lesson_code", SPOT_CHECK_LESSONS)
def test_spot_check_core_lessons_have_real_content(db_session, lesson_code):
    """抽查教材是否真有讲解、代码和练习，而不是只有标题。"""
    _seed(db_session)
    lesson = _lesson_by_code(db_session, lesson_code)
    content = lesson.content

    # 讲解
    assert len(content.learning_objectives.strip()) >= 30
    assert len(content.concept_explanation.strip()) >= 100
    assert len(content.plain_explanation.strip()) >= 60
    assert len(content.syntax_explanation.strip()) >= 50
    # 代码 + 逐行解释 + 输出
    assert content.example_code.count("\n") >= 3
    assert len(content.example_output.strip()) >= 10
    assert len(content.code_explanation.splitlines()) >= 3
    # 常见错误与错误分析都要写出原因
    assert len(content.common_mistakes.strip()) >= 30
    assert len(content.error_analysis.strip()) >= 30
    # 练习与测验
    assert len(_exercises_of(db_session, lesson)) >= 2
    assert len(_questions_of(db_session, lesson)) >= 6


# ---------------------------------------------------------------------------
# 4. 测验题：分类、题型、答案与知识点关联
# ---------------------------------------------------------------------------


def test_question_categories_per_lesson(db_session):
    _seed(db_session)

    for lesson in _lessons(db_session):
        questions = _questions_of(db_session, lesson)
        assert len(questions) >= 6, f"{lesson.code} 题目不足 6 道"
        categories = [question.category for question in questions]
        assert categories.count("基础理解") >= 2, f"{lesson.code} 基础理解题不足"
        assert categories.count("代码阅读") >= 2, f"{lesson.code} 代码阅读题不足"
        assert categories.count("应用练习") >= 2, f"{lesson.code} 应用题不足"


def test_course_covers_all_six_question_types(db_session):
    _seed(db_session)

    questions = db_session.scalars(select(Question)).all()
    types = {question.question_type for question in questions}
    assert REQUIRED_TYPES <= types
    # 多选题确实以多选形式存储答案
    multiple = [
        question
        for question in questions
        if question.question_type == "multiple_choice"
    ]
    assert multiple
    for question in multiple:
        assert len(question.correct_answer["values"]) >= 2
        assert len(question.options) >= 4


def test_questions_have_answers_explanations_and_knowledge_points(db_session):
    _seed(db_session)

    kp_ids = {
        kp.id for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    for lesson in _lessons(db_session):
        lesson_kp_ids = {kp.id for kp in lesson.knowledge_points}
        for question in _questions_of(db_session, lesson):
            assert question.knowledge_point_id in kp_ids
            assert question.knowledge_point_id in lesson_kp_ids
            assert question.stem.strip()
            assert question.explanation.strip(), f"{question.code} 缺少解析"
            assert question.correct_answer
            if question.question_type == "single_choice":
                keys = {option["key"] for option in question.options}
                assert question.correct_answer["value"] in keys
            if question.question_type == "true_false":
                assert isinstance(question.correct_answer["value"], bool)
            if question.question_type in {"short_answer", "code_writing"}:
                assert question.correct_answer["reference"].strip()


def test_question_stems_are_unique(db_session):
    _seed(db_session)

    stems = [question.stem for question in db_session.scalars(select(Question)).all()]
    assert len(stems) == len(set(stems))


# ---------------------------------------------------------------------------
# 5. 练习
# ---------------------------------------------------------------------------


def test_exercises_are_linked_and_answered(db_session):
    _seed(db_session)

    total = 0
    for lesson in _lessons(db_session):
        exercises = _exercises_of(db_session, lesson)
        assert len(exercises) >= 2, f"{lesson.code} 练习不足 2 个"
        lesson_kp_ids = {kp.id for kp in lesson.knowledge_points}
        for exercise in exercises:
            assert exercise.knowledge_point_id in lesson_kp_ids
            assert exercise.title.strip()
            assert (exercise.description or "").strip()
            assert (exercise.reference_answer or "").strip()
        total += len(exercises)
    assert total == EXPECTED_TEXTBOOK_EXERCISES


# ---------------------------------------------------------------------------
# 6. 种子规模、幂等与存量数据保留
# ---------------------------------------------------------------------------


def test_seed_scale_matches_content_definitions(db_session):
    _seed(db_session)

    assert total_questions() == EXPECTED_TEXTBOOK_QUESTIONS
    assert sum(len(chapter["lessons"]) for chapter in TEXTBOOK) == EXPECTED_LESSONS
    assert total_exercises() == EXPECTED_TEXTBOOK_EXERCISES

    textbook_questions = db_session.scalars(
        select(Question).where(Question.code.like("q-pb-%"))
    ).all()
    assert len(textbook_questions) == EXPECTED_TEXTBOOK_QUESTIONS


def test_seed_is_idempotent(db_session):
    _seed(db_session)
    counts = {
        "chapters": len(db_session.scalars(select(Chapter)).all()),
        "lessons": len(db_session.scalars(select(Lesson)).all()),
        "kps": len(db_session.scalars(select(KnowledgePoint)).all()),
        "contents": len(db_session.scalars(select(CourseContent)).all()),
        "exercises": len(db_session.scalars(select(Exercise)).all()),
        "questions": len(db_session.scalars(select(Question)).all()),
    }

    stats = seed_textbook(db_session)
    assert stats["chapters_created"] == 0
    assert stats["lessons_created"] == 0
    assert stats["knowledge_points_created"] == 0
    assert stats["contents_created"] == 0
    assert stats["exercises_created"] == 0
    assert stats["questions_created"] == 0

    assert counts == {
        "chapters": len(db_session.scalars(select(Chapter)).all()),
        "lessons": len(db_session.scalars(select(Lesson)).all()),
        "kps": len(db_session.scalars(select(KnowledgePoint)).all()),
        "contents": len(db_session.scalars(select(CourseContent)).all()),
        "exercises": len(db_session.scalars(select(Exercise)).all()),
        "questions": len(db_session.scalars(select(Question)).all()),
    }


def test_legacy_knowledge_points_and_questions_are_preserved(db_session):
    """31 个旧知识点与 93 道旧题必须按原 id / code 保留，学习历史才不丢。"""
    seed_courses(db_session)
    seed_questions(db_session)
    before_kps = {
        kp.id: kp.code for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    before_questions = {
        question.code: question.id
        for question in db_session.scalars(select(Question)).all()
    }
    assert len(before_kps) == EXPECTED_LEGACY_KPS
    assert len(before_questions) == EXPECTED_LEGACY_QUESTIONS

    seed_textbook(db_session)

    after_kps = {
        kp.id: kp.code for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    after_questions = {
        question.code: question.id
        for question in db_session.scalars(select(Question)).all()
    }
    # id 与 code 都不变：先修关系、题目 code、历史记录都按它们引用
    for kp_id, code in before_kps.items():
        assert after_kps[kp_id] == code
    for code, question_id in before_questions.items():
        assert after_questions[code] == question_id
    # 旧课时的题目仍然挂在可用知识点上，没有被孤立
    linked_kp_ids = {
        link.knowledge_point_id
        for link in db_session.scalars(select(LessonKnowledgePoint)).all()
    }
    orphan = [
        question.code
        for question in db_session.scalars(select(Question)).all()
        if question.knowledge_point_id not in linked_kp_ids
    ]
    assert orphan == []


def test_other_seeds_still_run_after_textbook(db_session):
    """教材种子之后，题库与课程目录种子仍能执行（不因结构调整而报错）。"""
    _seed(db_session)

    assert seed_questions(db_session)["updated"] == EXPECTED_LEGACY_QUESTIONS
    assert seed_course_catalog(db_session)["directions"] == 5
    assert seed_textbook(db_session)["lessons_created"] == 0


def test_learning_plan_can_reference_lesson_knowledge_points(api_env):
    """学习计划按知识点排期，课时知识点必须都能被计划使用。"""
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "三个月内掌握 Python 基础语法",
            "current_level": "L1",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
            "mastered_kp_codes": [],
        },
    )
    assert resp.status_code == 201, resp.text
    plan = resp.json()
    draft = plan["pending_version"]
    assert draft is not None, "创建计划后应有待确认草稿版本"
    items = draft["items"]
    assert items

    db = factory()
    try:
        lesson_kp_codes = {
            kp.code
            for link in db.scalars(select(LessonKnowledgePoint)).all()
            for kp in db.scalars(
                select(KnowledgePoint).where(
                    KnowledgePoint.id == link.knowledge_point_id
                )
            ).all()
        }
        assert lesson_kp_codes
        for item in items:
            # 计划里的每个知识点都来自某个课时
            assert item["knowledge_point_code"] in lesson_kp_codes
            assert item["estimated_minutes"] > 0
    finally:
        db.close()

    # 确认后草稿生效，排期结果保持一致
    plan_id = plan["id"]
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    current = resp.json()["current_version"]
    assert current is not None
    assert [item["day_index"] for item in current["items"]] == sorted(
        item["day_index"] for item in current["items"]
    )


# ---------------------------------------------------------------------------
# 7. 内容状态流转
# ---------------------------------------------------------------------------


def test_content_status_follows_review_flow(db_session):
    _seed(db_session)
    service = TextbookService(db_session)
    lesson_code = "python-basics-12-l01"

    # reviewed → draft → reviewed → published
    assert service.set_content_status(lesson_code, "draft").status == "draft"
    assert service.set_content_status(lesson_code, "reviewed").status == "reviewed"
    assert service.set_content_status(lesson_code, "published").status == "published"
    # published 只能退回 reviewed
    assert service.set_content_status(lesson_code, "reviewed").status == "reviewed"


def test_publish_is_blocked_when_module_missing(db_session):
    _seed(db_session)
    service = TextbookService(db_session)
    lesson = _lesson_by_code(db_session, "python-basics-12-l01")
    lesson.content.example_output = ""
    db_session.commit()

    with pytest.raises(Exception) as excinfo:
        service.set_content_status("python-basics-12-l01", "published")
    assert "示例输出" in str(excinfo.value)


def test_draft_content_is_hidden_by_default(db_session):
    _seed(db_session)
    service = TextbookService(db_session)
    lesson_code = "python-basics-12-l01"
    service.set_content_status(lesson_code, "draft")

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        service.get_lesson_textbook(lesson_code)
    assert excinfo.value.status_code == 404

    # 明确要求查看草稿时可以拿到
    draft = service.get_lesson_textbook(lesson_code, include_draft=True)
    assert draft.content is not None
    assert draft.content.status == "draft"


# ---------------------------------------------------------------------------
# 8. 内容验收（10 项检查）
# ---------------------------------------------------------------------------


def test_audit_passes_all_checks(db_session):
    _seed(db_session)

    report = TextbookService(db_session).audit_course("python-basics")
    assert report.passed is True
    assert report.total_chapters == EXPECTED_CHAPTERS
    assert report.total_lessons == EXPECTED_LESSONS
    assert report.total_exercises == EXPECTED_TEXTBOOK_EXERCISES
    assert report.lesson_failures == []
    assert [check.key for check in report.checks] == [
        "chapters",
        "lessons",
        "content_modules",
        "code",
        "beginner_friendly",
        "exercises",
        "questions",
        "scope",
        "duplication",
        "plan_reference",
    ]
    for check in report.checks:
        assert check.passed, f"{check.name} 未通过：{check.issues[:3]}"


def test_audit_detects_broken_content(db_session):
    """审计要能真的抓到问题，否则「通过」没有意义。"""
    _seed(db_session)
    lesson = _lesson_by_code(db_session, "python-basics-10-l01")
    lesson.content.plain_explanation = "循环就是重复。"
    lesson.content.learning_objectives = "无"
    db_session.commit()

    report = TextbookService(db_session).audit_course("python-basics")
    assert report.passed is False
    failed = {check.key for check in report.checks if not check.passed}
    assert {"content_modules", "beginner_friendly"} <= failed
    assert any(
        failure.lesson_code == "python-basics-10-l01"
        for failure in report.lesson_failures
    )


# ---------------------------------------------------------------------------
# 9. 教材接口
# ---------------------------------------------------------------------------


def test_course_textbook_api_returns_outline(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get("/api/v1/courses/python-basics/textbook")
    assert resp.status_code == 200, resp.text
    outline = resp.json()
    assert outline["course_code"] == "python-basics"
    assert outline["chapter_count"] == EXPECTED_CHAPTERS
    assert outline["lesson_count"] == EXPECTED_LESSONS
    assert outline["content_count"] == EXPECTED_LESSONS
    assert outline["reviewed_count"] == EXPECTED_LESSONS
    assert [chapter["code"] for chapter in outline["chapters"]] == CHAPTER_CODES
    first_lesson = outline["chapters"][0]["lessons"][0]
    assert first_lesson["has_content"] is True
    assert first_lesson["content_status"] == "reviewed"
    assert first_lesson["knowledge_point_count"] >= 1

    # 按状态筛选
    resp = client.get(
        "/api/v1/courses/python-basics/textbook", params={"status": "draft"}
    )
    assert resp.status_code == 200
    assert resp.json()["lesson_count"] == EXPECTED_LESSONS
    assert all(
        lesson["lessons"] == [] or lesson["lessons"][0]["content_status"] == "draft"
        for lesson in resp.json()["chapters"]
    )


def test_course_textbook_api_unknown_course(api_env):
    client, _factory = api_env
    assert client.get("/api/v1/courses/not-exist/textbook").status_code == 404


def test_lesson_textbook_api_returns_full_content(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get("/api/v1/lessons/python-basics-12-l01/textbook")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["lesson_code"] == "python-basics-12-l01"
    assert payload["chapter_code"] == "python-basics-12"
    assert payload["has_content"] is True

    content = payload["content"]
    for field, _label in CONTENT_FIELDS:
        assert content[field], f"{field} 为空"
    assert content["status"] == "reviewed"

    assert payload["knowledge_points"]
    assert payload["exercises"]
    assert len(payload["questions"]) >= 6
    question = payload["questions"][0]
    assert question["category"] in {"基础理解", "代码阅读", "应用练习"}
    assert question["explanation"]
    assert question["correct_answer"]

    assert client.get("/api/v1/lessons/not-exist/textbook").status_code == 404


def test_content_status_api(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    # reviewed → published 允许
    resp = client.patch(
        "/api/v1/lessons/python-basics-12-l01/content-status",
        json={"status": "published"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "published"
    assert resp.json()["previous_status"] == "reviewed"

    # published → draft 不允许（必须先退回 reviewed）
    resp = client.patch(
        "/api/v1/lessons/python-basics-12-l01/content-status",
        json={"status": "draft"},
    )
    assert resp.status_code == 409

    # 非法状态值被 schema 拒绝
    resp = client.patch(
        "/api/v1/lessons/python-basics-12-l01/content-status",
        json={"status": "done"},
    )
    assert resp.status_code == 422


def test_textbook_audit_api(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get("/api/v1/courses/python-basics/textbook/audit")
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["passed"] is True
    assert len(report["checks"]) == 10
    assert report["total_questions"] >= EXPECTED_TEXTBOOK_QUESTIONS


# ---------------------------------------------------------------------------
# 10. 迁移：category 列与存量回填
# ---------------------------------------------------------------------------


def _make_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def test_question_category_migration_backfills_legacy_questions(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "textbook_migration.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)

    cfg = _make_config()
    # 先在最新结构上写入题库数据，再退回「新增 category 之前」的版本，
    # 这样能真实检验升级时的回填逻辑，而不是只检查列是否存在。
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        seed_courses(session)
        seed_questions(session)
        assert session.scalar(select(func.count()).select_from(Question)) == (
            EXPECTED_LEGACY_QUESTIONS
        )
    finally:
        session.close()

    command.downgrade(cfg, "d3e4f5a6b7c8")
    assert "category" not in {
        column["name"] for column in inspect(engine).get_columns("question_bank")
    }
    session = factory()
    try:
        # 降级只去掉新列，题目本身一条都不能少
        assert session.scalar(select(func.count()).select_from(Question)) == (
            EXPECTED_LEGACY_QUESTIONS
        )
    finally:
        session.close()

    # 升级后列存在，且存量题全部回填了分类
    command.upgrade(cfg, "head")
    session = factory()
    try:
        categories = session.scalars(select(Question.category)).all()
        assert len(categories) == EXPECTED_LEGACY_QUESTIONS
        assert all(category for category in categories)
        assert set(categories) <= {"基础理解", "代码阅读", "应用练习"}
        # 答案与解析未被迁移破坏
        question = session.scalars(
            select(Question).where(Question.code == "q-python-basics-01-01-1")
        ).one()
        assert question.correct_answer
        assert question.explanation.strip()
        # 答题记录表结构未被触碰
        tables = set(inspect(engine).get_table_names())
        assert {"quiz_attempts", "quiz_answers", "mistakes", "review_tasks"} <= tables
    finally:
        session.close()
    engine.dispose()


def test_metadata_matches_head_schema(tmp_path, monkeypatch):
    """模型定义与迁移后的表结构一致，避免后续 alembic check 漂移。"""
    db_path = tmp_path / "textbook_head.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)

    command.upgrade(_make_config(), "head")
    engine = create_engine(url)
    try:
        migrated = {
            column["name"]
            for column in inspect(engine).get_columns("question_bank")
        }
        expected = {column.name for column in Question.__table__.columns}
        assert migrated == expected
        assert "category" in migrated
    finally:
        engine.dispose()
