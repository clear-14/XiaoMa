"""阶段 4A 验收测试：Python 进阶与工程实践、数据库与 Python 数据库开发。

覆盖：
- 章节 / 课时结构与课程目录一致，每节课有实质教学内容；
- 15 个内容模块齐全，代码示例、输出与逐行解释完整；
- 每节 6 道测验题，覆盖三种认知层次与全部六种题型，答案与解析齐备；
- 练习数量与知识点关联正确，跨课时不串；
- 知识点先修关系不与新顺序冲突，课程级先修与基础课程正确衔接；
- 技术版本规范（SQLAlchemy 2.0 风格、Alembic 批处理、SQLite 外键开关）；
- 幂等写入与既有数据不受影响；
- 教材可通过既有接口查询，内容状态可流转。
"""

import pytest
from sqlalchemy import func, select

from app.models.course import (
    Chapter,
    Course,
    CourseContent,
    CourseKnowledgePointPrerequisite,
    CoursePrerequisite,
    Exercise,
    KnowledgePoint,
    Lesson,
    LessonKnowledgePoint,
)
from app.seed.advanced import CHAPTERS as ADVANCED_CHAPTERS
from app.seed.course_catalog_seed import seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.database import CHAPTERS as DATABASE_CHAPTERS
from app.seed.phase4a_seed import seed_phase4a
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.seed.textbook_writer import CONTENT_MODULES

ADVANCED = "python-advanced"
DATABASE = "python-database"
NEW_COURSES = (ADVANCED, DATABASE)
EXPECTED_CHAPTERS = {ADVANCED: 10, DATABASE: 9}
EXPECTED_LESSONS = {ADVANCED: 12, DATABASE: 11}

# 需求列出的主题关键字：必须能在章或课时标题里找到
REQUIRED_TOPICS = {
    ADVANCED: [
        "面向对象",
        "类与对象",
        "封装",
        "继承",
        "多态",
        "推导式",
        "迭代",
        "生成器",
        "装饰器",
        "上下文管理器",
        "类型注解",
        "虚拟环境",
        "依赖",
        "目录结构",
        "日志",
        "配置",
    ],
    DATABASE: [
        "数据库基础",
        "SQL 查询",
        "SQLite",
        "主键",
        "外键",
        "JOIN",
        "索引",
        "事务",
        "SQLAlchemy",
        "ORM",
        "Session",
        "CRUD",
        "Alembic",
    ],
}


def _seed(db) -> None:
    # 与 CLI 的初始化顺序一致：基础课内容 → 课程目录 → 题库 → 基础教材 → 阶段 4A
    seed_courses(db)
    seed_course_catalog(db)
    seed_questions(db)
    seed_textbook(db)
    seed_phase4a(db)


def _chapters(db, course_code: str) -> list[Chapter]:
    course = db.scalars(select(Course).where(Course.code == course_code)).one()
    return sorted(
        (item for item in course.chapters if item.deleted_at is None),
        key=lambda item: item.order_index,
    )


def _lessons(db, course_code: str) -> list[Lesson]:
    return [
        lesson
        for chapter in _chapters(db, course_code)
        for lesson in sorted(
            (item for item in chapter.lessons if item.deleted_at is None),
            key=lambda item: item.order_index,
        )
    ]


# ---------------------------------------------------------------------------
# 一、结构
# ---------------------------------------------------------------------------


def test_courses_exist_with_expected_structure(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        chapters = _chapters(db_session, code)
        assert len(chapters) == EXPECTED_CHAPTERS[code]
        assert [item.order_index for item in chapters] == list(
            range(1, len(chapters) + 1)
        )
        for chapter in chapters:
            assert chapter.title.strip()
            lessons = sorted(chapter.lessons, key=lambda item: item.order_index)
            assert lessons, f"{chapter.code} 没有课时"
            assert [item.order_index for item in lessons] == list(
                range(1, len(lessons) + 1)
            )
        assert len(_lessons(db_session, code)) == EXPECTED_LESSONS[code]


def test_lesson_codes_follow_catalog_rule(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            assert lesson.code.startswith(f"{lesson.chapter.code}-lesson-")
            assert lesson.estimated_minutes and lesson.estimated_minutes > 0


def test_every_required_topic_is_covered(db_session):
    _seed(db_session)

    for code, topics in REQUIRED_TOPICS.items():
        titles = " ".join(
            [chapter.title for chapter in _chapters(db_session, code)]
            + [lesson.title for lesson in _lessons(db_session, code)]
        )
        missing = [topic for topic in topics if topic not in titles]
        assert not missing, f"{code} 缺少主题：{missing}"


# ---------------------------------------------------------------------------
# 二、教学内容
# ---------------------------------------------------------------------------


def test_every_lesson_has_all_modules_with_real_content(db_session):
    _seed(db_session)

    assert len(CONTENT_MODULES) == 15
    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            content = lesson.content
            assert content is not None, f"{lesson.code} 没有教学内容"
            assert content.status == "reviewed"
            for field, _key, label in CONTENT_MODULES:
                value = (getattr(content, field) or "").strip()
                assert value, f"{lesson.code} 的「{label}」为空"
                minimum = 2 if field == "example_output" else 10
                assert len(value) >= minimum, f"{lesson.code} 的「{label}」过短"


def test_code_examples_and_explanations_are_complete(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            content = lesson.content
            assert content.example_code.strip()
            assert any(
                token in content.example_code
                for token in ("print", "def ", "for ", "=", "import", "SELECT")
            ), f"{lesson.code} 示例代码不像可运行片段"
            lines = [
                line
                for line in content.code_explanation.splitlines()
                if line.strip()
            ]
            assert len(lines) >= 5, f"{lesson.code} 逐行解释不足 5 条"
            assert content.example_output.strip()


def test_plain_explanation_is_beginner_friendly(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            content = lesson.content
            plain = content.plain_explanation.strip()
            assert len(plain) >= 60, f"{lesson.code} 通俗解释过短"
            assert plain != content.concept_explanation.strip()


# ---------------------------------------------------------------------------
# 三、练习与测验
# ---------------------------------------------------------------------------


def test_each_lesson_has_two_exercises_linked_to_its_knowledge_points(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            kp_ids = {kp.id for kp in lesson.knowledge_points if kp.deleted_at is None}
            exercises = db_session.scalars(
                select(Exercise).where(Exercise.knowledge_point_id.in_(kp_ids))
            ).all()
            assert len(exercises) >= 2, f"{lesson.code} 练习不足 2 个"
            for exercise in exercises:
                assert exercise.knowledge_point_id in kp_ids
                assert exercise.reference_answer.strip()
                assert exercise.explanation.strip()


def test_each_lesson_has_six_questions_covering_all_layers(db_session):
    _seed(db_session)

    from app.models.quiz import Question

    type_counter: dict[str, int] = {}
    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            kp_ids = {kp.id for kp in lesson.knowledge_points if kp.deleted_at is None}
            questions = db_session.scalars(
                select(Question).where(Question.knowledge_point_id.in_(kp_ids))
            ).all()
            assert len(questions) >= 6, f"{lesson.code} 题目不足 6 道"
            categories = [item.category for item in questions]
            for category in ("基础理解", "代码阅读", "应用练习"):
                assert categories.count(category) >= 2, (
                    f"{lesson.code} 的 {category} 题不足 2 道"
                )
            for question in questions:
                type_counter[question.question_type] = (
                    type_counter.get(question.question_type, 0) + 1
                )
                assert question.explanation.strip()
                assert question.correct_answer
                if question.question_type in {"single_choice", "multiple_choice"}:
                    assert question.options, f"{question.code} 缺少选项"

    for question_type in (
        "single_choice",
        "multiple_choice",
        "true_false",
        "code_analysis",
        "code_writing",
        "short_answer",
    ):
        assert type_counter.get(question_type, 0) > 0, f"缺少题型 {question_type}"


# ---------------------------------------------------------------------------
# 四、先修关系与课程衔接
# ---------------------------------------------------------------------------


def test_knowledge_point_prerequisites_follow_course_order(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        position = {}
        for chapter in _chapters(db_session, code):
            for lesson in chapter.lessons:
                for kp in lesson.knowledge_points:
                    position[kp.id] = (chapter.order_index, kp.order_index)

        edges = db_session.scalars(select(KnowledgePoint).where(
            KnowledgePoint.deleted_at.is_(None)
        )).all()
        checked = 0
        for kp in edges:
            if kp.id not in position:
                continue
            for prerequisite in kp.prerequisites:
                if prerequisite.id not in position:
                    continue
                checked += 1
                assert position[prerequisite.id] < position[kp.id], (
                    f"{kp.code} 的前置 {prerequisite.code} 排在后面"
                )
        assert checked > 0, f"{code} 没有建立知识点先修关系"


def test_course_level_prerequisites_are_correct(db_session):
    _seed(db_session)

    advanced = db_session.scalars(
        select(Course).where(Course.code == ADVANCED)
    ).one()
    database = db_session.scalars(
        select(Course).where(Course.code == DATABASE)
    ).one()

    course_codes = {
        course.id: course.code
        for course in db_session.scalars(select(Course)).all()
    }
    advanced_pre = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(
                CoursePrerequisite.course_id == advanced.id
            )
        ).all()
    }
    database_pre = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(
                CoursePrerequisite.course_id == database.id
            )
        ).all()
    }
    assert advanced_pre == {"python-basics"}
    assert database_pre == {ADVANCED}


def test_new_courses_reference_basics_knowledge_points(db_session):
    _seed(db_session)

    for code in NEW_COURSES:
        course = db_session.scalars(select(Course).where(Course.code == code)).one()
        linked = db_session.scalars(
            select(CourseKnowledgePointPrerequisite).where(
                CourseKnowledgePointPrerequisite.course_id == course.id
            )
        ).all()
        assert linked, f"{code} 没有登记入学知识点"
        kp_codes = {
            kp.id: kp.code
            for kp in db_session.scalars(select(KnowledgePoint)).all()
        }
        codes = {kp_codes[link.knowledge_point_id] for link in linked}
        assert all(item.startswith("python-basics-") for item in codes), codes


# ---------------------------------------------------------------------------
# 五、技术版本规范
# ---------------------------------------------------------------------------


def test_sqlalchemy_content_uses_2x_style(db_session):
    _seed(db_session)

    orm_lessons = [
        lesson
        for lesson in _lessons(db_session, DATABASE)
        if "ORM" in lesson.chapter.title or "SQLAlchemy" in lesson.chapter.title
    ]
    assert orm_lessons
    joined = "\n".join(lesson.content.example_code for lesson in orm_lessons)
    assert "DeclarativeBase" in joined
    assert "Mapped[" in joined
    assert "mapped_column(" in joined
    # 1.x 的旧写法不应出现在教材示例里
    assert "declarative_base()" not in joined
    assert "session.query(" not in joined


def test_migration_lesson_uses_batch_mode_and_revision_chain(db_session):
    _seed(db_session)

    migrations = [
        lesson
        for lesson in _lessons(db_session, DATABASE)
        if lesson.chapter.code == "python-database-09"
    ]
    assert migrations
    joined = "\n".join(
        lesson.content.example_code + lesson.content.syntax_explanation
        for lesson in migrations
    )
    assert "down_revision" in joined
    assert "batch_alter_table" in joined
    assert "downgrade" in joined


def test_sqlite_lessons_mention_foreign_key_pragma(db_session):
    _seed(db_session)

    joined = "\n".join(
        lesson.content.example_code + lesson.content.syntax_explanation
        for lesson in _lessons(db_session, DATABASE)
    )
    assert "PRAGMA foreign_keys" in joined


# ---------------------------------------------------------------------------
# 六、不提前使用未学内容
# ---------------------------------------------------------------------------


def test_first_chapters_do_not_use_later_syntax(db_session):
    _seed(db_session)

    advanced_early = [
        lesson
        for lesson in _lessons(db_session, ADVANCED)
        if lesson.chapter.order_index <= 3
    ]
    joined = "\n".join(item.content.example_code for item in advanced_early)
    assert "yield" not in joined
    assert "contextlib" not in joined

    database_early = [
        lesson
        for lesson in _lessons(db_session, DATABASE)
        if lesson.chapter.order_index == 1
    ]
    joined_sql = "\n".join(item.content.example_code for item in database_early)
    assert "JOIN" not in joined_sql
    assert "GROUP BY" not in joined_sql


# ---------------------------------------------------------------------------
# 七、幂等与既有数据
# ---------------------------------------------------------------------------


def test_seed_is_idempotent(db_session):
    _seed(db_session)

    def snapshot() -> dict[str, int]:
        return {
            "chapters": db_session.scalar(select(func.count()).select_from(Chapter)),
            "lessons": db_session.scalar(select(func.count()).select_from(Lesson)),
            "kps": db_session.scalar(select(func.count()).select_from(KnowledgePoint)),
            "contents": db_session.scalar(
                select(func.count()).select_from(CourseContent)
            ),
            "exercises": db_session.scalar(select(func.count()).select_from(Exercise)),
            "links": db_session.scalar(
                select(func.count()).select_from(LessonKnowledgePoint)
            ),
        }

    before = snapshot()
    stats = seed_phase4a(db_session)
    assert snapshot() == before
    for code in NEW_COURSES:
        assert stats[code]["contents_created"] == 0
        assert stats[code]["exercises_created"] == 0
        assert stats[code]["questions_created"] == 0


def test_basics_course_is_untouched_by_phase4a(db_session):
    _seed(db_session)

    basics = db_session.scalars(select(Course).where(Course.code == "python-basics")).one()
    basics_lessons = [
        lesson
        for chapter in basics.chapters
        for lesson in chapter.lessons
        if lesson.deleted_at is None
    ]
    assert len(basics_lessons) == 29
    assert basics.version == "1.1.0"


# ---------------------------------------------------------------------------
# 八、接口
# ---------------------------------------------------------------------------


def test_api_returns_course_textbook(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    for code in NEW_COURSES:
        resp = client.get(f"/api/v1/courses/{code}/textbook")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["course_code"] == code
        assert data["chapter_count"] == EXPECTED_CHAPTERS[code]
        assert data["lesson_count"] == EXPECTED_LESSONS[code]
        assert data["content_count"] == EXPECTED_LESSONS[code]
        assert data["reviewed_count"] == EXPECTED_LESSONS[code]


def test_api_lesson_textbook_and_audit(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
        lesson_code = _lessons(db, ADVANCED)[0].code
    finally:
        db.close()

    resp = client.get(f"/api/v1/lessons/{lesson_code}/textbook")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    content = data["content"]
    for field in (
        "learning_objectives",
        "why_learn",
        "concept_explanation",
        "plain_explanation",
        "syntax_explanation",
        "example_code",
        "code_explanation",
        "example_output",
        "common_mistakes",
        "error_analysis",
        "beginner_exercises",
        "advanced_exercises",
        "quiz_note",
        "summary",
        "next_lesson",
    ):
        assert content[field]
    assert len(data["questions"]) >= 6
    assert len(data["exercises"]) >= 2

    for code in NEW_COURSES:
        audit = client.get(f"/api/v1/courses/{code}/textbook/audit")
        assert audit.status_code == 200, audit.text
        report = audit.json()
        assert report["passed"] is True, [
            (item["name"], item["issues"]) for item in report["checks"] if not item["passed"]
        ]


def test_api_content_status_transition(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
        lesson_code = _lessons(db, DATABASE)[0].code
    finally:
        db.close()

    resp = client.patch(
        f"/api/v1/lessons/{lesson_code}/content-status",
        json={"status": "published"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "published"

    # 已发布的内容不能跳级退回草稿，必须先回到 reviewed
    resp = client.patch(
        f"/api/v1/lessons/{lesson_code}/content-status",
        json={"status": "draft"},
    )
    assert resp.status_code == 409

    resp = client.patch(
        f"/api/v1/lessons/{lesson_code}/content-status",
        json={"status": "reviewed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "reviewed"

# ---------------------------------------------------------------------------
# 九、示例代码可运行、输出与教材一致
# ---------------------------------------------------------------------------


def test_example_code_runs_and_matches_declared_output(db_session):
    """真实执行每节课的示例代码，比对教材写的示例输出。

    这是「示例代码完整」之外更强的一条：代码能跑、输出对得上。
    含 Traceback 的课时是刻意演示异常，跳过；时间戳按占位比较。
    """
    import contextlib
    import io
    import re

    _seed(db_session)

    def normalize(lines: list[str]) -> list[str]:
        return [
            re.sub(r"\d{2}:\d{2}:\d{2}", "HH:MM:SS", line.strip())
            for line in lines
            if line.strip()
        ]

    for code in NEW_COURSES:
        for lesson in _lessons(db_session, code):
            content = lesson.content
            if "Traceback" in (content.example_output or ""):
                continue
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(
                    compile(content.example_code, lesson.code, "exec"),
                    {"__name__": "__main__"},
                )
            actual = normalize((stdout.getvalue() + "\n" + stderr.getvalue()).splitlines())
            declared = normalize(content.example_output.splitlines())
            assert actual == declared, f"{lesson.code} 示例输出与真实运行不一致"
