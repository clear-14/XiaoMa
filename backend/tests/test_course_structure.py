"""阶段 1 课程数据结构测试。

覆盖需求中的 10 项验收点：
1. 课程可以创建和查询
2. 章节可以关联课程
3. 课时可以关联章节
4. 知识点可以关联课时
5. 练习和测验可以关联知识点
6. 不存在无效外键
7. 不存在重复唯一 slug
8. 数据迁移能够正常升级
9. 原有数据没有丢失
10. 重复查询不会产生副作用
"""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

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
from app.seed.course_seed import seed_courses
from app.seed.question_seed import seed_questions
from app.services.course_service import CourseService

BACKEND_DIR = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 造数据辅助
# ---------------------------------------------------------------------------


def _make_course(db, code: str = "demo", *, publish_status: str = "published") -> Course:
    course = Course(
        code=code,
        name=f"课程 {code}",
        description="演示课程",
        direction="python",
        difficulty="beginner",
        recommended_level="L0",
        version="1.0.0",
        publish_status=publish_status,
        sort_order=1,
    )
    db.add(course)
    db.flush()
    return course


def _make_chain(db, course: Course) -> tuple[Chapter, Lesson, KnowledgePoint]:
    """建出 课程 → 章节 → 课时 → 知识点 的完整链路。"""
    chapter = Chapter(
        course=course,
        code=f"{course.code}-01",
        title="第一章",
        description="章节介绍",
        order_index=1,
    )
    db.add(chapter)
    db.flush()

    lesson = Lesson(
        chapter=chapter,
        code=f"{course.code}-01-lesson-01",
        title="第一课时",
        description="课时说明",
        difficulty="beginner",
        estimated_minutes=20,
        order_index=1,
    )
    db.add(lesson)
    db.flush()

    kp = KnowledgePoint(
        chapter=chapter,
        code=f"{course.code}-01-01",
        name="变量与赋值",
        learning_goal="理解变量与赋值",
        difficulty="beginner",
        estimated_minutes=10,
        mastery_criteria="能正确命名变量并赋值",
        order_index=1,
    )
    db.add(kp)
    db.flush()

    db.add(
        LessonKnowledgePoint(
            lesson_id=lesson.id, knowledge_point_id=kp.id, order_index=1
        )
    )
    db.flush()
    return chapter, lesson, kp


def _table_counts(db) -> dict[str, int]:
    return {
        table: db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in (
            "courses",
            "chapters",
            "lessons",
            "knowledge_points",
            "lesson_knowledge_points",
            "exercises",
            "question_bank",
        )
    }


# ---------------------------------------------------------------------------
# 1. 课程可以创建和查询
# ---------------------------------------------------------------------------


def test_course_can_be_created_and_queried(db_session):
    service = CourseService(db_session)
    created = service.create_course(
        code="python-advanced",
        name="Python 进阶",
        description="进阶课程",
        direction="python",
        difficulty="intermediate",
        recommended_level="L1",
        estimated_minutes=300,
    )

    assert created.code == "python-advanced"
    assert created.slug == "python-advanced"  # slug 复用唯一业务标识
    assert created.publish_status == "draft"
    assert created.chapter_count == 0
    assert created.lesson_count == 0

    detail = service.get_course_detail("python-advanced")
    assert detail.name == "Python 进阶"
    assert detail.direction == "python"
    assert detail.difficulty == "intermediate"
    assert detail.recommended_level == "L1"
    assert detail.estimated_minutes == 300
    assert detail.chapters == []


def test_course_filters_by_direction_difficulty_and_level(db_session):
    service = CourseService(db_session)
    service.create_course(
        code="py-a", name="A", direction="python", difficulty="beginner",
        recommended_level="L0", publish_status="published",
    )
    service.create_course(
        code="py-b", name="B", direction="python", difficulty="advanced",
        recommended_level="L2", publish_status="published",
    )
    service.create_course(
        code="data-a", name="C", direction="data", difficulty="beginner",
        recommended_level="L0", publish_status="published",
    )

    assert {c.code for c in service.list_courses(direction="python")} == {"py-a", "py-b"}
    assert {
        c.code for c in service.list_courses(difficulty="beginner")
    } == {"py-a", "data-a"}
    assert {c.code for c in service.list_courses(recommended_level="L2")} == {"py-b"}
    assert {
        c.code
        for c in service.list_courses(direction="python", difficulty="advanced")
    } == {"py-b"}


def test_course_publish_status_isolated(db_session):
    """草稿/已发布/已归档在列表中可区分。"""
    service = CourseService(db_session)
    service.create_course(code="draft-course", name="草稿课", publish_status="draft")
    service.create_course(
        code="live-course", name="已发布课", publish_status="published"
    )
    service.create_course(
        code="old-course", name="归档课", publish_status="archived"
    )

    published = {c.code for c in service.list_courses()}
    assert "live-course" in published
    assert "draft-course" not in published
    assert "old-course" not in published

    assert {c.code for c in service.list_courses(publish_status="draft")} == {
        "draft-course"
    }
    assert {c.code for c in service.list_courses(publish_status="archived")} == {
        "old-course"
    }
    assert {
        c.code for c in service.list_courses(publish_status="all")
    } == {"draft-course", "live-course", "old-course"}

    # 状态切换后列表随之变化
    service.update_publish_status("draft-course", "published")
    assert "draft-course" in {c.code for c in service.list_courses()}
    service.update_publish_status("draft-course", "archived")
    assert "draft-course" not in {c.code for c in service.list_courses()}


# ---------------------------------------------------------------------------
# 2~4. 章节 → 课时 → 知识点 关联
# ---------------------------------------------------------------------------


def test_chapter_links_to_course(db_session):
    course = _make_course(db_session)
    chapter, _lesson, _kp = _make_chain(db_session, course)
    db_session.commit()

    detail = CourseService(db_session).get_course_detail("demo")
    assert [ch.code for ch in detail.chapters] == ["demo-01"]
    assert detail.chapters[0].title == "第一章"
    assert detail.chapter_count == 1

    assert chapter.course_id == course.id
    assert chapter in course.chapters


def test_lesson_links_to_chapter(db_session):
    course = _make_course(db_session)
    chapter, lesson, _kp = _make_chain(db_session, course)
    db_session.commit()

    service = CourseService(db_session)
    lessons = service.list_lessons("demo", "demo-01")
    assert [item.code for item in lessons] == ["demo-01-lesson-01"]
    assert lessons[0].title == "第一课时"
    assert lessons[0].knowledge_point_count == 1

    detail = service.get_lesson("demo-01-lesson-01")
    assert detail.module.code == "demo-01"
    assert detail.course.code == "demo"
    assert lesson.chapter_id == chapter.id


def test_knowledge_point_links_to_lesson(db_session):
    course = _make_course(db_session)
    _chapter, lesson, kp = _make_chain(db_session, course)
    db_session.commit()

    service = CourseService(db_session)
    lesson_detail = service.get_lesson("demo-01-lesson-01")
    assert [item.code for item in lesson_detail.knowledge_points] == ["demo-01-01"]

    kp_detail = service.get_knowledge_point("demo-01-01")
    assert kp_detail.lesson is not None
    assert kp_detail.lesson.code == "demo-01-lesson-01"
    assert kp.lesson is not None and kp.lesson.id == lesson.id

    # 课时下知识点与章节下知识点一致（两条归属保持同步）
    assert [item.code for item in lesson.knowledge_points] == [kp.code]


def test_lesson_content_is_one_per_lesson(db_session):
    course = _make_course(db_session)
    _chapter, lesson, _kp = _make_chain(db_session, course)
    db_session.add(
        CourseContent(
            lesson_id=lesson.id,
            learning_objectives="掌握变量",
            concept_explanation="变量是名字",
            syntax_explanation="name = value",
            example_code="x = 1",
            code_explanation="把 1 赋给 x",
            common_mistakes="使用关键字命名",
            summary="变量用于保存值",
        )
    )
    db_session.flush()

    detail = CourseService(db_session).get_lesson("demo-01-lesson-01")
    assert detail.content is not None
    assert detail.content.example_code == "x = 1"

    # 同一课时不允许第二份教学内容（lesson_id 唯一）
    db_session.add(CourseContent(lesson_id=lesson.id, summary="重复内容"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 5. 练习和测验关联知识点
# ---------------------------------------------------------------------------


def test_exercise_and_question_link_to_knowledge_point(db_session):
    course = _make_course(db_session)
    _chapter, _lesson, kp = _make_chain(db_session, course)
    db_session.add(
        Exercise(
            knowledge_point_id=kp.id,
            code="ex-demo-01-01-1",
            title="练习：定义变量",
            description="定义变量 x 并赋值为 1",
            exercise_type="coding",
            difficulty="beginner",
            reference_answer="x = 1",
            explanation="赋值语句",
            order_index=1,
        )
    )
    db_session.add(
        Question(
            code="q-demo-01-01-1",
            knowledge_point_id=kp.id,
            question_type="single_choice",
            stem="下列哪个是合法变量名？",
            options=[{"key": "A", "text": "1x"}, {"key": "B", "text": "name"}],
            correct_answer={"value": "B"},
            explanation="变量名不能以数字开头",
            difficulty="beginner",
            source="builtin",
            status="approved",
            validation_status="builtin",
        )
    )
    db_session.commit()

    service = CourseService(db_session)
    exercises = service.list_exercises("demo-01-01")
    assert [item.code for item in exercises] == ["ex-demo-01-01-1"]
    assert exercises[0].reference_answer == "x = 1"

    # 默认不泄露答案与解析
    questions = service.list_questions("demo-01-01")
    assert [item.code for item in questions] == ["q-demo-01-01-1"]
    assert questions[0].correct_answer is None
    assert questions[0].explanation is None

    with_answer = service.list_questions("demo-01-01", include_answer=True)
    assert with_answer[0].correct_answer == {"value": "B"}
    assert with_answer[0].explanation == "变量名不能以数字开头"

    kp_detail = service.get_knowledge_point("demo-01-01")
    assert kp_detail.exercise_count == 1
    assert kp_detail.question_count == 1


# ---------------------------------------------------------------------------
# 6. 不存在无效外键
# ---------------------------------------------------------------------------


def test_invalid_foreign_keys_are_rejected(db_session):
    """课时引用不存在的章节、归属引用不存在的课时/知识点，都必须被数据库拒绝。"""
    db_session.add(
        Lesson(chapter_id=uuid4(), code="bad-lesson", title="无效课时", order_index=1)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        LessonKnowledgePoint(
            lesson_id=uuid4(), knowledge_point_id=uuid4(), order_index=1
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        Exercise(
            knowledge_point_id=uuid4(),
            code="bad-exercise",
            title="无效练习",
            exercise_type="coding",
            difficulty="beginner",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_all_foreign_keys_valid_after_seed(db_session):
    """种子数据写入后，全库 foreign_key_check 无违规。"""
    seed_courses(db_session)
    violations = db_session.execute(text("PRAGMA foreign_key_check")).all()
    assert violations == []


# ---------------------------------------------------------------------------
# 7. 不存在重复唯一 slug
# ---------------------------------------------------------------------------


def test_duplicate_slug_is_rejected(db_session):
    service = CourseService(db_session)
    service.create_course(code="unique-course", name="唯一课程")

    with pytest.raises(HTTPException) as exc:
        service.create_course(code="unique-course", name="重复课程")
    assert exc.value.status_code == 409

    # 数据库层唯一约束同样生效（绕过 Service 也写不进去）
    db_session.add(Course(code="unique-course", name="绕过 Service"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_lesson_and_exercise_codes_are_unique(db_session):
    course = _make_course(db_session)
    _chapter, _lesson, kp = _make_chain(db_session, course)
    # 先提交基础数据：后续因唯一约束失败而 rollback 时不能把课程链路一起回滚
    db_session.commit()

    db_session.add(
        Lesson(chapter_id=_chapter.id, code="demo-01-lesson-01", title="重复课时")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        Exercise(
            knowledge_point_id=kp.id,
            code="ex-dup",
            title="练习",
            exercise_type="coding",
            difficulty="beginner",
        )
    )
    db_session.flush()
    db_session.add(
        Exercise(
            knowledge_point_id=kp.id,
            code="ex-dup",
            title="重复练习",
            exercise_type="coding",
            difficulty="beginner",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 8~9. 迁移可升级 + 原有数据不丢失
# ---------------------------------------------------------------------------


def _make_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def test_migration_upgrade_keeps_legacy_data(tmp_path, monkeypatch):
    """旧库升级：新表建出、旧数据行数不变、章节自动生成课时并归属知识点。"""
    db_path = tmp_path / "upgrade.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)

    cfg = _make_config()
    # 先停在阶段 1 之前的 head，构造「升级前」数据
    command.upgrade(cfg, "5a9439936da5")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO courses (id, code, name, description, created_at, updated_at) "
                "VALUES (lower(hex(randomblob(16))), 'python-basics', 'Python 通用基础', "
                "'desc', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        course_id = conn.execute(text("SELECT id FROM courses")).scalar_one()
        for index, code in enumerate(("python-basics-01", "python-basics-02"), start=1):
            conn.execute(
                text(
                    "INSERT INTO chapters (id, course_id, code, title, description, "
                    "order_index, created_at, updated_at) VALUES "
                    "(lower(hex(randomblob(16))), :cid, :code, :title, 'd', :oi, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"cid": course_id, "code": code, "title": f"章节{index}", "oi": index},
            )
        for chapter_id, chapter_code in conn.execute(
            text("SELECT id, code FROM chapters")
        ).all():
            for seq in range(1, 4):
                conn.execute(
                    text(
                        "INSERT INTO knowledge_points (id, chapter_id, code, name, "
                        "learning_goal, difficulty, estimated_minutes, mastery_criteria, "
                        "resources, order_index, created_at, updated_at) VALUES "
                        "(lower(hex(randomblob(16))), :ch, :code, :name, 'goal', "
                        "'beginner', 10, 'crit', NULL, :oi, CURRENT_TIMESTAMP, "
                        "CURRENT_TIMESTAMP)"
                    ),
                    {
                        "ch": chapter_id,
                        "code": f"{chapter_code}-0{seq}",
                        "name": f"知识点{seq}",
                        "oi": seq,
                    },
                )

    with engine.connect() as conn:
        before = {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("courses", "chapters", "knowledge_points")
        }
    engine.dispose()

    # 升级到阶段 1 之后的 head
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        assert {
            "lessons",
            "course_contents",
            "exercises",
            "course_versions",
            "lesson_knowledge_points",
        } <= tables

        after = {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("courses", "chapters", "knowledge_points")
        }
        assert after == before  # 原有数据没有丢失

        meta = conn.execute(
            text(
                "SELECT direction, difficulty, recommended_level, estimated_minutes, "
                "version, publish_status FROM courses"
            )
        ).one()
        assert meta == ("python", "beginner", "L0", 60, "1.0.0", "published")

        lesson_count = conn.execute(text("SELECT COUNT(*) FROM lessons")).scalar_one()
        link_count = conn.execute(
            text("SELECT COUNT(*) FROM lesson_knowledge_points")
        ).scalar_one()
        orphan = conn.execute(
            text(
                "SELECT COUNT(*) FROM knowledge_points kp WHERE NOT EXISTS ("
                "SELECT 1 FROM lesson_knowledge_points x "
                "WHERE x.knowledge_point_id = kp.id)"
            )
        ).scalar_one()
        assert lesson_count == 2
        assert link_count == 6
        assert orphan == 0
        assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()


def test_migration_downgrade_removes_only_new_structure(tmp_path, monkeypatch):
    """降级只回滚阶段 1 新增结构，原课程/章节/知识点数据保留。"""
    db_path = tmp_path / "downgrade.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)

    cfg = _make_config()
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO courses (id, code, name, description, created_at, updated_at) "
                "VALUES (lower(hex(randomblob(16))), 'c1', '课程', 'd', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()

    command.downgrade(cfg, "5a9439936da5")

    engine = create_engine(url)
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        assert "lessons" not in tables
        assert "course_versions" not in tables
        course_columns = {c["name"] for c in inspect(conn).get_columns("courses")}
        assert "publish_status" not in course_columns
        assert "direction" not in course_columns
        assert conn.execute(text("SELECT COUNT(*) FROM courses")).scalar_one() == 1
    engine.dispose()


# ---------------------------------------------------------------------------
# 10. 重复查询不会产生副作用
# ---------------------------------------------------------------------------


def test_repeated_queries_have_no_side_effects(db_session):
    seed_courses(db_session)
    service = CourseService(db_session)

    before_counts = _table_counts(db_session)
    before_snapshot = service.get_course_detail("python-basics").model_dump()

    for _ in range(3):
        service.list_courses()
        service.get_course_detail("python-basics")
        service.list_chapters("python-basics")
        service.list_lessons("python-basics", "python-basics-01")
        service.get_lesson("python-basics-01-lesson-01")
        service.get_knowledge_point("python-basics-01-01")
        service.list_exercises("python-basics-01-01")
        service.list_questions("python-basics-01-01")

    after_counts = _table_counts(db_session)
    after_snapshot = service.get_course_detail("python-basics").model_dump()

    assert before_counts == after_counts
    assert before_snapshot == after_snapshot


def test_seed_is_idempotent_for_lesson_layer(db_session):
    """种子重复执行不会产生重复课时或重复归属。"""
    first = seed_courses(db_session)
    second = seed_courses(db_session)

    assert first["lessons"] == 14
    assert second["lessons"] == 14
    assert first["knowledge_points"] == second["knowledge_points"] == 31

    lesson_count = db_session.execute(
        text("SELECT COUNT(*) FROM lessons")
    ).scalar_one()
    link_count = db_session.execute(
        text("SELECT COUNT(*) FROM lesson_knowledge_points")
    ).scalar_one()
    assert lesson_count == 14
    assert link_count == 31

    # 每个知识点只归属一个课时
    duplicated = db_session.execute(
        text(
            "SELECT knowledge_point_id, COUNT(*) c FROM lesson_knowledge_points "
            "GROUP BY knowledge_point_id HAVING c > 1"
        )
    ).all()
    assert duplicated == []


# ---------------------------------------------------------------------------
# 课程版本
# ---------------------------------------------------------------------------


def test_save_course_version_snapshot(db_session):
    course = _make_course(db_session)
    _make_chain(db_session, course)
    db_session.commit()

    service = CourseService(db_session)
    saved = service.save_version("demo", version="1.0.1", note="首次存档")
    assert saved.version == "1.0.1"
    assert saved.snapshot["course"]["code"] == "demo"
    assert saved.snapshot["modules"][0]["lessons"][0]["code"] == "demo-01-lesson-01"

    versions = service.list_versions("demo")
    assert [item.version for item in versions] == ["1.0.1"]

    fetched = service.get_version("demo", "1.0.1")
    assert fetched.snapshot == saved.snapshot

    # 同版本号不覆盖
    with pytest.raises(HTTPException) as exc:
        service.save_version("demo", version="1.0.1")
    assert exc.value.status_code == 409


def test_course_version_defaults_to_course_version(db_session):
    course = _make_course(db_session)
    db_session.commit()

    service = CourseService(db_session)
    saved = service.save_version("demo", note="按课程当前版本存档")
    assert saved.version == course.version == "1.0.0"


# ---------------------------------------------------------------------------
# API 层
# ---------------------------------------------------------------------------


def test_course_api_exposes_new_structure(api_env):
    client, factory = api_env
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()

    resp = client.get("/api/v1/courses")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert item["slug"] == "python-basics"
    assert item["direction"] == "python-fundamentals"
    assert item["publish_status"] == "published"
    assert item["lesson_count"] == 14
    assert item["knowledge_point_count"] == 31

    resp = client.get("/api/v1/courses/python-basics/chapters/python-basics-01/lessons")
    assert resp.status_code == 200
    lessons = resp.json()
    assert [item["code"] for item in lessons] == [
        "python-basics-01-lesson-01",
        "python-basics-01-lesson-02",
    ]

    resp = client.get("/api/v1/lessons/python-basics-01-lesson-01")
    assert resp.status_code == 200
    lesson = resp.json()
    assert lesson["module"]["code"] == "python-basics-01"
    assert lesson["course"]["code"] == "python-basics"
    assert len(lesson["knowledge_points"]) == 2

    resp = client.get("/api/v1/courses/python-basics/versions")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post(
        "/api/v1/courses/python-basics/versions", json={"version": "1.0.1"}
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == "1.0.1"

    resp = client.patch(
        "/api/v1/courses/python-basics/status", json={"publish_status": "archived"}
    )
    assert resp.status_code == 200
    assert resp.json()["publish_status"] == "archived"


def test_course_api_filters_and_errors(api_env):
    client, factory = api_env
    db = factory()
    try:
        seed_courses(db)
        seed_questions(db)
    finally:
        db.close()

    resp = client.get("/api/v1/courses?direction=python-fundamentals")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/v1/courses?difficulty=nonsense")
    assert resp.status_code == 422

    resp = client.get("/api/v1/lessons/no-such-lesson")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "课时不存在"}

    resp = client.get("/api/v1/courses/python-basics/chapters/no-such-chapter/lessons")
    assert resp.status_code == 404

    resp = client.get("/api/v1/knowledge-points/python-basics-01-01/exercises")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.get("/api/v1/knowledge-points/python-basics-01-01/questions")
    assert resp.status_code == 200
    questions = resp.json()
    assert len(questions) == 3
    assert all(item["correct_answer"] is None for item in questions)
