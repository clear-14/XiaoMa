"""阶段 4C 验收测试：Python 大模型 API 应用开发课程。

覆盖需求给出的四部分要求：
1. 课程章节完整（16 章 32 课时，需求列出的 20 个主题逐条落到课时）；
2. 重点内容讲到（Key 安全保存、httpx 调用兼容 API、Base URL 与模型名、messages 组织、
   流式输出、JSON 处理、工具调用、上下文长度、超时限流与异常）；
3. 综合项目齐备（模型配置 / API 调用 / 消息管理 / 多轮上下文 / 流式输出 / 错误处理，
   且 API Key 必须来自环境变量）；
4. 教材口径正确（以 OpenAI 兼容调用方式为基础，不把某家临时参数写成通用规范）。
另外验证练习与测验合规、先修关系正确、写入幂等、其它课程不受影响。
"""

import re

import pytest
from sqlalchemy import func, select

from app.core.curriculum import LLM_SCOPE
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
from app.seed.llm import CHAPTERS as LLM_CHAPTERS
from app.seed.phase4c_seed import seed_phase4c
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.seed.textbook_writer import CONTENT_MODULES

LLM = "llm-api"
EXPECTED_CHAPTERS = 16
EXPECTED_LESSONS = 32

# 需求列出的 20 个主题 → 必须出现在章或课时标题里的关键字
REQUIRED_TOPICS = [
    "大语言模型",
    "模型服务商",
    "API Key",
    "调用大模型",
    "OpenAI 兼容",
    "消息结构",
    "System Prompt",
    "Prompt 设计",
    "多轮对话",
    "上下文管理",
    "Streaming",
    "JSON 结构化输出",
    "Function Calling",
    "Tool Calling",
    "上下文窗口",
    "费用",
    "超时",
    "重试",
    "安全",
    "综合项目",
]

# 综合项目的 6 个组成部分 → 必须对应到第 16 章的课时
PROJECT_COMPONENTS = {
    "模型配置": "模型配置与项目骨架",
    "API 调用": "消息管理与 API 调用",
    "消息管理": "消息管理与 API 调用",
    "多轮上下文": "多轮上下文与上下文裁剪",
    "流式输出": "流式输出与前端透传",
    "错误处理": "错误处理、测试与交付",
}

# 重点内容必须有代码落点（课时标题 → 示例代码或语法说明里必须出现的关键片段）
KEY_POINTS = {
    "Base URL、模型名称与请求响应结构": ["/chat/completions", "choices", "Bearer"],
    "Key 从哪里来、怎么存": ["LLM_API_KEY", "os.environ"],
    "第一次调用：httpx 打通接口": ["httpx", "Bearer"],
    "三种角色与提示分工": ["system", "user", "assistant"],
    "SSE 协议与增量解析": ["data:", "delta"],
    "JSON 模式与 Schema 约束": ["response_format"],
    "函数声明与调用返回": ["tool_calls", "json.loads"],
    "超时预算与退避重试": ["Retry-After", "MAX_RETRIES"],
    "用量统计、费用估算与限流": ["usage", "cost_of"],
}

# 明显的真实密钥形态（教学里出现的正则 `sk-[A-Za-z0-9]{8,}` 不算）
REAL_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9]{16,}")
LITERAL_KEY_PATTERN = re.compile(
    r"(?:api_?key|LLM_API_KEY)\s*=\s*[\"'][A-Za-z0-9\-_]{12,}[\"']"
)


def _seed(db) -> None:
    # 与 CLI 的初始化顺序一致：基础课内容 → 课程目录 → 题库 → 基础教材 → 阶段 4C
    seed_courses(db)
    seed_course_catalog(db)
    seed_questions(db)
    seed_textbook(db)
    seed_phase4c(db)


def _chapters(db, course_code: str = LLM) -> list[Chapter]:
    course = db.scalars(select(Course).where(Course.code == course_code)).first()
    return sorted(course.chapters, key=lambda item: item.order_index)


def _lessons(db, course_code: str = LLM) -> list[Lesson]:
    lessons: list[Lesson] = []
    for chapter in _chapters(db, course_code):
        lessons.extend(sorted(chapter.lessons, key=lambda item: item.order_index))
    return lessons


# ---------------------------------------------------------------------------
# 一、课程章节完整
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

    catalog_lessons = sum(len(chapter["lessons"]) for chapter in LLM_CHAPTERS)
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


def test_project_components_covered(db_session):
    _seed(db_session)
    project = [item for item in _chapters(db_session) if item.title.startswith("综合项目")]
    assert len(project) == 1 and project[0].order_index == EXPECTED_CHAPTERS
    titles = [lesson.title for lesson in project[0].lessons]
    assert len(titles) == 5
    for component, lesson_title in PROJECT_COMPONENTS.items():
        assert lesson_title in titles, f"项目组成「{component}」没有对应课时"
    assert all(lesson.content and lesson.content.example_code for lesson in project[0].lessons)


# ---------------------------------------------------------------------------
# 二、每节课有实质教学内容
# ---------------------------------------------------------------------------


def test_every_lesson_has_required_modules(db_session):
    _seed(db_session)
    with_exchange = 0
    for lesson in _lessons(db_session):
        content = lesson.content
        assert content is not None, lesson.code
        for field, _key, label in CONTENT_MODULES:
            value = (getattr(content, field) or "").strip()
            assert value, f"{lesson.code} 缺少{label}"
            assert len(value) >= 10, f"{lesson.code} 的{label}过短"
        output = content.example_output
        assert len(output.strip()) >= 10, f"{lesson.code} 示例输出过短"
        if "请求" in output and "响应" in output:
            with_exchange += 1
        lines = [line for line in content.code_explanation.splitlines() if line.strip()]
        assert len(lines) >= 5, f"{lesson.code} 逐行解释只有 {len(lines)} 条"
    # 涉及真实调用的章节必须给出请求与响应；概念类课时给出的是运行结果
    # 至少 5 节给出「请求 + 响应」的完整对照（其余课时是概念或本地运行结果）
    assert with_exchange >= 5, f"只有 {with_exchange} 节课展示了请求与响应"


def test_lesson_textbook_api_maps_all_modules(api_env):
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
        "learning_objectives",
        "concept_explanation",
        "syntax_explanation",
        "example_code",
        "code_explanation",
        "example_output",
        "common_mistakes",
        "beginner_exercises",
        "quiz_note",
        "summary",
    ):
        assert content[field], f"{field} 为空"


# ---------------------------------------------------------------------------
# 三、示例代码可用，且遵守兼容协议
# ---------------------------------------------------------------------------


def test_example_code_is_valid_python(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        try:
            compile(lesson.content.example_code, lesson.code, "exec")
        except SyntaxError as exc:  # pragma: no cover - 失败时用于定位
            pytest.fail(f"{lesson.code} 示例代码语法错误：{exc}")


def test_key_never_appears_in_course_code(db_session):
    """API Key 只能从环境变量读取：示例代码与语法说明里不得出现密钥字面量。"""
    _seed(db_session)
    for lesson in _lessons(db_session):
        blob = lesson.content.example_code + "\n" + lesson.content.syntax_explanation
        assert not REAL_KEY_PATTERN.search(blob), f"{lesson.code} 里出现了疑似真实 Key"
        assert not LITERAL_KEY_PATTERN.search(blob), f"{lesson.code} 里写死了 Key 字面量"
        assert "sk-proj" not in blob and "sk-ant" not in blob

    # 讲 Key 的那一节必须示范从环境变量读取，且示例里不能出现赋值式硬编码
    key_lesson = next(item for item in _lessons(db_session) if item.title == "Key 从哪里来、怎么存")
    code = key_lesson.content.example_code
    assert "os.environ" in code
    assert "LLM_API_KEY" in code


def test_key_lesson_covers_masking_and_gitignore(db_session):
    _seed(db_session)
    lesson = next(item for item in _lessons(db_session) if item.title == "Key 从哪里来、怎么存")
    blob = lesson.content.example_code + lesson.content.syntax_explanation
    assert ".gitignore" in blob or "gitignore" in blob
    assert ".env" in blob
    module_text = "\n".join(
        (getattr(lesson.content, field) or "") for field, _key, _label in CONTENT_MODULES
    )
    assert "脱敏" in module_text or "mask" in module_text


def test_key_points_have_code_anchors(db_session):
    _seed(db_session)
    by_title = {lesson.title: lesson.content for lesson in _lessons(db_session)}
    for title, markers in KEY_POINTS.items():
        content = by_title[title]
        blob = content.example_code + content.syntax_explanation
        for marker in markers:
            assert marker in blob, f"《{title}》未体现 {marker}"


def test_compat_protocol_is_the_basis(db_session):
    """教材以稳定的兼容协议为基础：同一套请求字段贯穿多章。"""
    _seed(db_session)
    corpus = "\n".join(
        lesson.content.example_code + lesson.content.syntax_explanation
        for lesson in _lessons(db_session)
    )
    for marker in (
        "/chat/completions",
        "Bearer",
        '"messages"',
        "choices",
        "usage",
        "finish_reason",
        "delta",
        "response_format",
        "tool_calls",
    ):
        assert marker in corpus, f"兼容协议字段 {marker} 未出现"

    # 服务商差异只能作为「可选能力」出现，不能写成统一规范
    provider_lesson = next(
        item for item in _lessons(db_session) if item.title == "服务商生态与兼容协议"
    )
    text = "\n".join(
        (getattr(provider_lesson.content, field) or "") for field, _key, _label in CONTENT_MODULES
    )
    assert ("各有" in text) or ("不同" in text) or ("差异" in text)


def test_no_late_terms_in_early_chapters(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        chapter_order = lesson.chapter.order_index
        blob = lesson.content.example_code + "\n" + lesson.content.syntax_explanation
        for term, intro_order in LLM_SCOPE:
            if chapter_order < intro_order:
                assert term not in blob, (
                    f"{lesson.code} 第 {chapter_order} 章提前使用了第 {intro_order} 章的术语 {term}"
                )


# ---------------------------------------------------------------------------
# 四、练习与测验合规
# ---------------------------------------------------------------------------


def test_exercises_linked_to_lesson_knowledge_points(db_session):
    _seed(db_session)
    total = 0
    for lesson in _lessons(db_session):
        kp_ids = {kp.id for kp in lesson.knowledge_points}
        kp_list = sorted(kp_ids)
        exercises = db_session.scalars(
            select(Exercise).where(Exercise.knowledge_point_id.in_(kp_list))
        ).all()
        assert len(exercises) >= 2, f"{lesson.code} 练习不足 2 道"
        total += len(exercises)
        for exercise in exercises:
            assert exercise.knowledge_point_id in kp_ids, (
                f"{exercise.code} 未挂在本课时知识点上"
            )
            assert exercise.reference_answer and exercise.explanation
    assert total == EXPECTED_LESSONS * 2


def test_question_distribution_and_types(db_session):
    _seed(db_session)
    type_counter: dict[str, int] = {}
    category_counter: dict[str, int] = {}
    total = 0
    for lesson in _lessons(db_session):
        questions = []
        for kp in lesson.knowledge_points:
            questions.extend(
                db_session.scalars(
                    select(Question).where(Question.knowledge_point_id == kp.id)
                ).all()
            )
        assert len(questions) >= 6, f"{lesson.code} 题目不足 6 道"
        total += len(questions)
        categories: dict[str, int] = {}
        for question in questions:
            type_counter[question.question_type] = type_counter.get(question.question_type, 0) + 1
            categories[question.category] = categories.get(question.category, 0) + 1
            category_counter[question.category] = category_counter.get(question.category, 0) + 1
            assert question.explanation
        for category in ("基础理解", "代码阅读", "应用练习"):
            assert categories.get(category, 0) >= 2, f"{lesson.code} 的{category}题不足 2 道"
    assert total == EXPECTED_LESSONS * 6
    assert set(type_counter) == {
        "single_choice",
        "multiple_choice",
        "true_false",
        "code_analysis",
        "code_writing",
        "short_answer",
    }


def test_knowledge_point_prerequisites_follow_course_order(db_session):
    _seed(db_session)
    lessons = _lessons(db_session)
    order = {kp.code: index for index, lesson in enumerate(lessons) for kp in lesson.knowledge_points}
    assert len(order) == EXPECTED_LESSONS

    seen: set[str] = set()
    for lesson in lessons:
        for kp in lesson.knowledge_points:
            for prerequisite in db_session.scalars(
                select(KnowledgePointPrerequisite).where(
                    KnowledgePointPrerequisite.knowledge_point_id == kp.id
                )
            ).all():
                code = db_session.get(KnowledgePoint, prerequisite.prerequisite_kp_id)
                assert code is not None
                assert order[code.code] < order[kp.code], f"{kp.code} 的先修倒挂"
                assert code.code in seen or order[code.code] < order[kp.code]
        seen.update(kp.code for kp in lesson.knowledge_points)


# ---------------------------------------------------------------------------
# 五、API 与审计
# ---------------------------------------------------------------------------


def test_api_outline_and_audit(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get(f"/api/v1/courses/{LLM}/textbook")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapter_count"] == EXPECTED_CHAPTERS
    assert data["lesson_count"] == EXPECTED_LESSONS
    assert data["content_count"] == EXPECTED_LESSONS
    assert data["reviewed_count"] == EXPECTED_LESSONS

    audit = client.get(f"/api/v1/courses/{LLM}/textbook/audit")
    assert audit.status_code == 200, audit.text
    report = audit.json()
    assert report["passed"] is True, [
        (item["name"], item["issues"]) for item in report["checks"] if not item["passed"]
    ]
    assert len(report["checks"]) == 10


def test_api_course_detail(api_env):
    client, factory = api_env
    db = factory()
    try:
        _seed(db)
    finally:
        db.close()

    resp = client.get(f"/api/v1/courses/{LLM}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recommended_level"] == "L1"
    assert any(item["code"] == "ai-llm" for item in data["directions"])
    assert len(data["chapters"]) == EXPECTED_CHAPTERS


# ---------------------------------------------------------------------------
# 六、依赖关系
# ---------------------------------------------------------------------------


def test_course_prerequisites(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == LLM)).first()
    course_codes = {item.id: item.code for item in db_session.scalars(select(Course)).all()}
    prerequisites = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(CoursePrerequisite.course_id == course.id)
        ).all()
    }
    assert prerequisites == {"python-advanced"}


def test_entry_knowledge_points_from_basics(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == LLM)).first()
    kp_codes = {kp.id: kp.code for kp in db_session.scalars(select(KnowledgePoint)).all()}
    required = {
        kp_codes[link.knowledge_point_id]
        for link in db_session.scalars(
            select(CourseKnowledgePointPrerequisite).where(
                CourseKnowledgePointPrerequisite.course_id == course.id
            )
        ).all()
    }
    assert required
    assert all(code.startswith("python-basics-") for code in required), required


# ---------------------------------------------------------------------------
# 七、幂等与其它课程不受影响
# ---------------------------------------------------------------------------


def test_seed_is_idempotent(db_session):
    _seed(db_session)
    first = (
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
        db_session.scalar(select(func.count()).select_from(Question)),
    )
    stats = seed_phase4c(db_session)
    second = (
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
        db_session.scalar(select(func.count()).select_from(Question)),
    )
    assert first == second
    assert stats["llm-api"]["contents_created"] == 0
    assert stats["llm-api"]["exercises_created"] == 0
    assert stats["llm-api"]["questions_created"] == 0


def test_other_courses_untouched(db_session):
    _seed(db_session)
    assert len(_chapters(db_session, "python-basics")) == 20
    assert len(_lessons(db_session, "python-basics")) == 29
    assert len(_chapters(db_session, "python-advanced")) == 10
    assert len(_chapters(db_session, "python-database")) == 9
    assert len(_chapters(db_session, "fastapi-backend")) == 16
    assert len(_chapters(db_session, "langgraph-agent")) == 28

    def snapshot() -> dict:
        return {
            code: (len(_chapters(db_session, code)), len(_lessons(db_session, code)))
            for code in (
                "python-basics",
                "python-advanced",
                "python-database",
                "fastapi-backend",
                "langgraph-agent",
                "software-engineering-deploy",
            )
        }

    before = snapshot()
    seed_phase4c(db_session)
    assert snapshot() == before


def test_lesson_knowledge_point_links(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        links = db_session.scalars(
            select(LessonKnowledgePoint).where(LessonKnowledgePoint.lesson_id == lesson.id)
        ).all()
        assert links, f"{lesson.code} 未关联知识点"
