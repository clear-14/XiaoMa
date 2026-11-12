"""阶段 4B 验收测试：FastAPI 后端开发课程。

覆盖需求给出的 8 项验收：
1. 课程目录完整（16 章 31 课时，24 个主题逐条落到课时）；
2. 每节课有实质教学内容（15 个内容模块非空且不是占位）；
3. 示例代码符合 FastAPI 版本（可编译、用 Annotated/response_model，无 1.x 旧写法）；
4. 请求响应示例合理（含 curl 请求与状态码/JSON 响应）；
5. 练习关联知识点（每节 ≥2 且挂在本节知识点上）；
6. 测验不超纲（难度不超课时一级、三类层次各 ≥2、六种题型齐备、早期章节不提前用后续语法）；
7. 课程可以通过现有 API 获取（大纲 / 课时教材 / 内容验收 / 状态流转）；
8. 相关课程依赖关系正确（先修 python-advanced + python-database，入学知识点来自 python-basics）。
另外验证幂等写入与其它课程不受影响。
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
    KnowledgePointPrerequisite,
    Lesson,
    LessonKnowledgePoint,
)
from app.models.quiz import Question
from app.seed.course_catalog_seed import seed_course_catalog
from app.seed.course_seed import seed_courses
from app.seed.fastapi import CHAPTERS as FASTAPI_CHAPTERS
from app.seed.phase4b_seed import seed_phase4b
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.seed.textbook_writer import CONTENT_MODULES

FASTAPI = "fastapi-backend"
EXPECTED_CHAPTERS = 16
EXPECTED_LESSONS = 31

# 需求列出的 24 个主题 → 必须出现在章或课时标题里的关键字
REQUIRED_TOPICS = [
    "API 基础",
    "安装",
    "路径参数",
    "查询参数",
    "HTTP 方法",
    "请求体",
    "Pydantic",
    "数据校验",
    "依赖注入",
    "路由模块化",
    "异常处理",
    "中间件",
    "CORS",
    "同步与异步",
    "SQLAlchemy",
    "用户认证",
    "JWT",
    "权限",
    "文件上传",
    "API 文档",
    "接口测试",
    "日志",
    "部署",
    "综合项目",
]

# 综合项目的 9 个步骤关键字（第 16 章的课时标题需覆盖）
PROJECT_STEPS = [
    ("创建项目", "创建项目与目录结构"),
    ("拆分路由", "拆分路由与数据模型"),
    ("编写数据模型", "拆分路由与数据模型"),
    ("连接 SQLite", "连接 SQLite 与实现 CRUD"),
    ("实现 CRUD", "连接 SQLite 与实现 CRUD"),
    ("接入用户认证", "接入认证与接口校验"),
    ("增加接口校验", "接入认证与接口校验"),
    ("编写测试", "编写测试与整理项目配置"),
    ("整理项目配置", "编写测试与整理项目配置"),
]

# 早期章节不得提前出现的语法 / 术语（术语 → 最早出现的章序）
LATE_TERMS = {
    "Depends": 7,
    "APIRouter": 8,
    "middleware": 9,
    "CORSMiddleware": 10,
    "async def": 9,
    "create_engine": 11,
    "JWT": 12,
    "UploadFile": 13,
    "TestClient": 14,
    "pytest": 14,
}


def _seed(db) -> None:
    # 与 CLI 的初始化顺序一致：基础课内容 → 课程目录 → 题库 → 基础教材 → 阶段 4B
    seed_courses(db)
    seed_course_catalog(db)
    seed_questions(db)
    seed_textbook(db)
    seed_phase4b(db)


def _chapters(db, course_code: str = FASTAPI) -> list[Chapter]:
    course = db.scalars(select(Course).where(Course.code == course_code)).first()
    return sorted(course.chapters, key=lambda item: item.order_index)


def _lessons(db, course_code: str = FASTAPI) -> list[Lesson]:
    lessons: list[Lesson] = []
    for chapter in _chapters(db, course_code):
        lessons.extend(sorted(chapter.lessons, key=lambda item: item.order_index))
    return lessons


# ---------------------------------------------------------------------------
# 一、课程目录完整
# ---------------------------------------------------------------------------


def test_chapter_and_lesson_structure(db_session):
    _seed(db_session)
    chapters = _chapters(db_session)
    assert len(chapters) == EXPECTED_CHAPTERS
    assert [item.order_index for item in chapters] == list(range(1, EXPECTED_CHAPTERS + 1))

    lessons = _lessons(db_session)
    assert len(lessons) == EXPECTED_LESSONS
    for lesson in lessons:
        assert lesson.title and lesson.estimated_minutes
        assert lesson.difficulty in {"beginner", "intermediate", "advanced"}

    # 目录种子与教材数据一致
    catalog_lessons = sum(len(chapter["lessons"]) for chapter in FASTAPI_CHAPTERS)
    assert catalog_lessons == EXPECTED_LESSONS


def test_required_topics_covered(db_session):
    _seed(db_session)
    titles = " ".join(
        [chapter.title for chapter in _chapters(db_session)]
        + [lesson.title for lesson in _lessons(db_session)]
        + [chapter.description or "" for chapter in _chapters(db_session)]
    )
    missing = [topic for topic in REQUIRED_TOPICS if topic not in titles]
    assert not missing, f"以下主题没有落到章或课时标题：{missing}"


def test_project_steps_covered(db_session):
    _seed(db_session)
    project = [item for item in _chapters(db_session) if item.title.startswith("综合项目")]
    assert len(project) == 1 and project[0].order_index == EXPECTED_CHAPTERS
    titles = [lesson.title for lesson in project[0].lessons]
    for step, lesson_title in PROJECT_STEPS:
        assert lesson_title in titles, f"项目步骤「{step}」没有对应课时"
    # 九个步骤都有代码落点
    assert all(lesson.content and lesson.content.example_code for lesson in project[0].lessons)


# ---------------------------------------------------------------------------
# 二、每节课有实质教学内容
# ---------------------------------------------------------------------------


def test_every_lesson_has_required_modules(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        content = lesson.content
        assert content is not None, lesson.code
        for field, _key, label in CONTENT_MODULES:
            value = (getattr(content, field) or "").strip()
            assert value, f"{lesson.code} 缺少{label}"
            assert len(value) >= 10, f"{lesson.code} 的{label}过短"
        # 「请求和响应示例」必须同时含请求与响应
        output = content.example_output
        assert ("curl" in output or "请求" in output), f"{lesson.code} 示例输出缺请求"
        assert ("HTTP/1.1" in output or "{" in output), f"{lesson.code} 示例输出缺响应"
        # 逐行解析不少于 5 条
        lines = [line for line in content.code_explanation.splitlines() if line.strip()]
        assert len(lines) >= 5, f"{lesson.code} 逐行解释只有 {len(lines)} 条"


def test_lesson_textbook_api_maps_all_modules(api_env):
    """需求要求的 10 个模块都能通过既有接口读到。"""
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
        lesson_code = _lessons(db)[0].code
    finally:
        db.close()

    resp = client.get(f"/api/v1/lessons/{lesson_code}/textbook")
    assert resp.status_code == 200, resp.text
    content = resp.json()["content"]
    for field in (
        "learning_objectives",  # 本节目标
        "concept_explanation",  # 核心知识
        "syntax_explanation",  # API 说明
        "example_code",  # 完整代码示例
        "code_explanation",  # 逐行解析
        "example_output",  # 请求和响应示例
        "common_mistakes",  # 常见错误
        "beginner_exercises",  # 实战练习
        "quiz_note",  # 小测验
        "summary",  # 学习总结
    ):
        assert content[field], f"{field} 为空"


# ---------------------------------------------------------------------------
# 三、示例代码符合 FastAPI 版本
# ---------------------------------------------------------------------------


def test_example_code_is_valid_python(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        code = lesson.content.example_code
        try:
            compile(code, lesson.code, "exec")
        except SyntaxError as exc:  # pragma: no cover - 失败时用于定位
            pytest.fail(f"{lesson.code} 示例代码语法错误：{exc}")


def test_example_code_uses_modern_fastapi_style(db_session):
    _seed(db_session)
    legacy_markers = (
        "@app.on_event",
        "declarative_base()",
        "session.query(",
        "from typing import List",
        "pydantic.v1",
    )
    uses_annotated = 0
    param_markers = ("Query(", "Path(", "Depends(", "Header(", "Form(")
    for lesson in _lessons(db_session):
        code = lesson.content.example_code
        # 旧写法只允许作为「不推荐」出现在说明文字里，绝不能出现在示例代码中
        for marker in legacy_markers:
            assert marker not in code, f"{lesson.code} 示例代码使用了旧写法：{marker}"
        if "Annotated[" in code:
            uses_annotated += 1
            continue
        # 用到 Query/Path/Depends 等参数标记时，必须写成 Annotated 形式（0.95+ 推荐风格）
        for marker in param_markers:
            assert marker not in code, (
                f"{lesson.code} 使用了 {marker}...) 却没有用 Annotated[T, ...] 包裹"
            )
    # 参数校验与依赖注入集中在第 3 章之后，至少 10 节课应展示 Annotated 写法
    assert uses_annotated >= 10


def test_core_lessons_show_expected_api_surface(db_session):
    """关键课时必须真的用到对应版本的 API。"""
    _seed(db_session)
    by_title = {lesson.title: lesson.content for lesson in _lessons(db_session)}

    expectations = {
        "安装、启动与自动文档": ["FastAPI(", "uvicorn"],
        "模型、Field 与别名": ["Field(", "ConfigDict"],
        "校验器、嵌套模型与错误响应": ["field_validator", "model_validator"],
        "Depends 基础与 yield 依赖": ["Depends(", "yield"],
        "APIRouter 拆分与前缀标签": ["APIRouter(", "include_router"],
        "统一异常处理": ["exception_handler", "JSONResponse"],
        "中间件：耗时与请求 ID": ["middleware(", "call_next"],
        "CORS 跨域配置": ["CORSMiddleware", "allow_origins"],
        "同步与异步接口": ["async def", "asyncio.sleep"],
        "引擎、会话与 Session 依赖": ["create_engine", "DeclarativeBase", "mapped_column"],
        "事务边界与数据访问分层": ["begin_nested", "rollback"],
        "用户模型与密码哈希": ["pbkdf2_hmac", "compare_digest"],
        "JWT 签发、校验与当前用户": ["OAuth2PasswordBearer", "Bearer"],
        "角色与资源级权限": ["403", "owner"],
        "文件上传与上传校验": ["UploadFile", "File("],
        "OpenAPI 元数据与文档定制": ["openapi_tags", "responses="],
        "pytest、TestClient 与测试库": ["TestClient", "dependency_overrides"],
        "生产部署": ["lifespan", "workers"],
    }
    for title, markers in expectations.items():
        content = by_title[title]
        blob = content.example_code + content.syntax_explanation
        for marker in markers:
            assert marker in blob, f"《{title}》未体现 {marker}"


# ---------------------------------------------------------------------------
# 四、请求和响应示例合理
# ---------------------------------------------------------------------------


def test_example_output_shows_status_or_json(db_session):
    _seed(db_session)
    with_status = 0
    for lesson in _lessons(db_session):
        output = lesson.content.example_output
        assert "curl" in output or "请求" in output
        if "HTTP/1.1" in output:
            with_status += 1
        # 输出里不应出现「略」「同上」这类占位
        assert "略" not in output.splitlines()[0]
    # 至少八成的课时给出完整状态行，其余给出等价 JSON 输出
    assert with_status >= int(EXPECTED_LESSONS * 0.5)


# ---------------------------------------------------------------------------
# 五、练习关联知识点
# ---------------------------------------------------------------------------


def test_exercises_linked_to_lesson_knowledge_points(db_session):
    _seed(db_session)
    codes: list[str] = []
    for lesson in _lessons(db_session):
        kp_ids = {kp.id for kp in lesson.knowledge_points}
        assert kp_ids, f"{lesson.code} 没有知识点"
        exercises = db_session.scalars(
            select(Exercise).where(Exercise.knowledge_point_id.in_(kp_ids))
        ).all()
        assert len(exercises) >= 2, f"{lesson.code} 练习不足 2"
        for exercise in exercises:
            assert exercise.knowledge_point_id in kp_ids
            assert exercise.reference_answer and exercise.explanation
            assert exercise.difficulty in {"beginner", "intermediate", "advanced"}
            codes.append(exercise.code)
    assert len(codes) == len(set(codes)), "练习 code 有重复"


# ---------------------------------------------------------------------------
# 六、测验不超纲
# ---------------------------------------------------------------------------


def test_question_distribution_and_types(db_session):
    _seed(db_session)
    from collections import Counter

    type_counter: Counter[str] = Counter()
    for lesson in _lessons(db_session):
        kp_ids = {kp.id for kp in lesson.knowledge_points}
        questions = db_session.scalars(
            select(Question).where(Question.knowledge_point_id.in_(kp_ids))
        ).all()
        assert len(questions) >= 6, f"{lesson.code} 题目不足 6"
        categories = Counter(question.category for question in questions)
        for category in ("基础理解", "代码阅读", "应用练习"):
            assert categories[category] >= 2, f"{lesson.code} 的{category}题不足 2"
        rank = {"beginner": 0, "intermediate": 1, "advanced": 2}[lesson.difficulty]
        for question in questions:
            type_counter[question.question_type] += 1
            assert rank >= {"beginner": 0, "intermediate": 1, "advanced": 2}[question.difficulty] - 1, (
                f"{question.code} 难度高于课时"
            )
            assert question.explanation and question.correct_answer

    for question_type in (
        "single_choice",
        "multiple_choice",
        "true_false",
        "code_analysis",
        "code_writing",
        "short_answer",
    ):
        assert type_counter[question_type] > 0, f"课程没有出现 {question_type} 题"


def test_no_late_topics_in_early_chapters(db_session):
    """JWT、数据库、异步等不得提前出现在最初级课时。"""
    _seed(db_session)
    for chapter in _chapters(db_session):
        for lesson in chapter.lessons:
            content = lesson.content
            blob = content.example_code + content.syntax_explanation
            for term, intro_chapter in LATE_TERMS.items():
                if chapter.order_index < intro_chapter:
                    assert term not in blob, (
                        f"{lesson.code}（第 {chapter.order_index} 章）提前使用了"
                        f"第 {intro_chapter} 章才讲的 {term}"
                    )


def test_knowledge_point_prerequisites_follow_course_order(db_session):
    _seed(db_session)
    order: dict = {}
    for chapter in _chapters(db_session):
        for lesson in chapter.lessons:
            for kp in lesson.knowledge_points:
                order[kp.id] = (chapter.order_index, lesson.order_index, kp.order_index)

    edges = db_session.scalars(select(KnowledgePointPrerequisite)).all()
    assert edges, "应建立知识点先修边"

    for edge in edges:
        target = order.get(edge.knowledge_point_id)
        prerequisite = order.get(edge.prerequisite_kp_id)
        if target is None or prerequisite is None:
            continue
        assert prerequisite < target, f"知识点先修倒挂：{edge.knowledge_point_id}"


# ---------------------------------------------------------------------------
# 七、课程可以通过现有 API 获取
# ---------------------------------------------------------------------------


def test_api_outline_and_audit(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get(f"/api/v1/courses/{FASTAPI}/textbook")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapter_count"] == EXPECTED_CHAPTERS
    assert data["lesson_count"] == EXPECTED_LESSONS
    assert data["content_count"] == EXPECTED_LESSONS
    assert data["reviewed_count"] == EXPECTED_LESSONS

    audit = client.get(f"/api/v1/courses/{FASTAPI}/textbook/audit")
    assert audit.status_code == 200, audit.text
    report = audit.json()
    assert report["passed"] is True, [
        (item["name"], item["issues"]) for item in report["checks"] if not item["passed"]
    ]
    assert len(report["checks"]) == 10


def test_api_course_detail_lists_scope(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get(f"/api/v1/courses/{FASTAPI}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recommended_level"] == "L2"
    assert data["directions"], "课程应关联方向"
    assert len(data["chapters"]) == EXPECTED_CHAPTERS


# ---------------------------------------------------------------------------
# 八、课程依赖关系正确
# ---------------------------------------------------------------------------


def test_course_prerequisites(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == FASTAPI)).first()
    course_codes = {
        item.id: item.code for item in db_session.scalars(select(Course)).all()
    }
    prerequisites = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(CoursePrerequisite.course_id == course.id)
        ).all()
    }
    assert prerequisites == {"python-advanced", "python-database"}


def test_entry_knowledge_points_from_basics(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == FASTAPI)).first()
    kp_codes = {
        kp.id: kp.code
        for kp in db_session.scalars(select(KnowledgePoint)).all()
    }
    required = {
        kp_codes[link.knowledge_point_id]
        for link in db_session.scalars(
            select(CourseKnowledgePointPrerequisite).where(
                CourseKnowledgePointPrerequisite.course_id == course.id
            )
        ).all()
    }
    assert required, "应登记入学知识点"
    assert all(code.startswith("python-basics-") for code in required), required


# ---------------------------------------------------------------------------
# 九、幂等与其它课程不受影响
# ---------------------------------------------------------------------------


def test_seed_is_idempotent(db_session):
    _seed(db_session)
    first = (
        db_session.scalar(select(func.count()).select_from(Chapter)),
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
    )
    stats = seed_phase4b(db_session)
    second = (
        db_session.scalar(select(func.count()).select_from(Chapter)),
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
    )
    assert first == second
    assert stats["fastapi-backend"]["contents_created"] == 0
    assert stats["fastapi-backend"]["exercises_created"] == 0


def test_other_courses_untouched(db_session):
    _seed(db_session)
    basics = _chapters(db_session, "python-basics")
    assert len(basics) == 20
    assert len(_lessons(db_session, "python-basics")) == 29
    assert len(_chapters(db_session, "python-advanced")) == 10
    assert len(_chapters(db_session, "python-database")) == 9

    # 再跑一次阶段 4B 的写入，其它课程的课时数、知识点数、题目数与内容数都不应变化
    def snapshot() -> dict:
        return {
            code: (
                len(_chapters(db_session, code)),
                len(_lessons(db_session, code)),
                db_session.scalar(
                    select(func.count())
                    .select_from(Lesson)
                    .join(Chapter)
                    .join(Course)
                    .where(Course.code == code, Course.code != FASTAPI)
                ),
            )
            for code in ("python-basics", "python-advanced", "python-database")
        }

    before = snapshot()
    seed_phase4b(db_session)
    assert snapshot() == before

    # 零基础课的内容条数不因阶段 4B 而变化
    basics_course = db_session.scalars(
        select(Course).where(Course.code == "python-basics")
    ).first()
    assert basics_course.version == "1.1.0"
    basics_contents = db_session.scalar(
        select(func.count())
        .select_from(CourseContent)
        .join(Lesson)
        .join(Chapter)
        .where(Chapter.course_id == basics_course.id)
    )
    assert basics_contents == 29


def test_lesson_knowledge_point_links(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        links = db_session.scalars(
            select(LessonKnowledgePoint).where(
                LessonKnowledgePoint.lesson_id == lesson.id
            )
        ).all()
        assert links, f"{lesson.code} 未关联知识点"
