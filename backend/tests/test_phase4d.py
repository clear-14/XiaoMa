"""阶段 4D 验收测试：LangGraph Agent 开发课程。

覆盖需求给出的六部分要求：

1. 课程章节完整（28 章 47 课时，需求列出的 28 个主题逐条成一章）；
2. 教学顺序正确（Agent 概念 → Graph 基础 → State/Node/Edge → 条件路由与流程控制
   → 大模型接入 → 工具调用 → 持久化与记忆 → 人工审批 → 子图 → 流式事件
   → FastAPI 集成 → 综合项目；前 3 章不出现任何框架代码）；
3. 重点内容讲到（State / Node / Edge / Conditional Edge / Checkpointer / Store /
   Interrupt / Subgraph / Streaming 各有独立课时与代码落点）；
4. 综合项目齐备（识别问题 / 读取课程知识 / 调用白名单工具 / 保存对话状态 /
   按条件选工作流 / FastAPI 接口 六项要求都有对应课时）；
5. 技术要求满足（重要 API 标注版本、不混用版本接口、示例代码可编译、
   不执行用户提交代码）；
6. 练习与测验合规、先修关系正确、写入幂等、其它课程不受影响。
"""

import io
import re
import warnings
from contextlib import redirect_stdout

import pytest
from sqlalchemy import func, select

from app.core.curriculum import LANGGRAPH_SCOPE
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
from app.seed.langgraph import CHAPTERS as LG_CHAPTERS
from app.seed.langgraph import COURSE_CODE, META, TOPICS
from app.seed.phase4d_seed import seed_phase4d
from app.seed.question_seed import seed_questions
from app.seed.textbook_seed import seed_textbook
from app.seed.textbook_writer import CONTENT_MODULES

LG = COURSE_CODE
EXPECTED_CHAPTERS = 28
EXPECTED_LESSONS = 47
EXPECTED_QUESTIONS = 282
EXPECTED_EXERCISES = 94

# 9 个重点教学要求 → (章号, 主课标题, 该章示例代码或语法说明里必须出现的关键片段)
KEY_POINTS = {
    "State：状态结构与状态更新": (
        6,
        "状态结构与类型约束",
        ["TypedDict", "state[", "return"],
    ),
    "Node：节点函数与输入输出": (
        7,
        "节点是什么",
        ["def ", "state", "return"],
    ),
    "Edge：节点之间的连接": (
        8,
        "边与入口出口",
        ["add_edge", "START", "END"],
    ),
    "Conditional Edge：条件判断与路由": (
        13,
        "路由函数与条件边",
        ["def dispatch", "add_conditional_edges", "END"],
    ),
    "Checkpointer：线程内状态持久化": (
        20,
        "线程与检查点",
        ["InMemorySaver", "thread_id", "get_state"],
    ),
    "Store：跨线程长期存储": (
        21,
        "跨线程长期存储",
        ["InMemoryStore", "runtime.store", "put"],
    ),
    "Interrupt：暂停并等待人工输入": (
        22,
        "中断与恢复",
        ["interrupt(", "Command(resume", "__interrupt__"],
    ),
    "Subgraph：模块化 Agent 与子图调用": (
        23,
        "子图定义与调用",
        ["add_node", "compile", "xray"],
    ),
    "Streaming：不同流式事件与处理": (
        24,
        "stream_mode 各模式",
        ["stream_mode", "values", "messages"],
    ),
}

# 综合项目的 6 项要求 → (对应课时标题, 内容里必须出现的关键片段)
PROJECT_COMPONENTS = {
    "能识别用户问题": ("需求拆解与图设计", ["intent", "classify"]),
    "能读取课程相关知识": ("状态与条件路由", ["retrieve", "read_chapter"]),
    "能调用允许使用的工具": ("模型配置与工具层", ["ALLOWED", "convert_to_openai_tool"]),
    "能保存对话状态": ("持久化与人工介入", ["checkpointer", "thread_id"]),
    "能根据条件选择工作流": ("状态与条件路由", ["RULES", "add_conditional_edges"]),
    "能通过 FastAPI 提供接口": ("FastAPI 接口与测试", ["/ask", "/approve"]),
}

# 教材必须写明的版本事实（以本机实测环境为准，不混用 V1 / V2 接口）
VERSION_MARKERS = [
    "1.2.20",  # langgraph
    "1.7.6",  # langchain-core
    "4.3.1",  # langgraph-checkpoint
    "LangGraphDeprecatedSinceV10",  # create_react_agent 的弃用告警
    "langchain.agents",  # 弃用后的替代入口
    "runtime.store",  # Store 的正确取法（替代旧教程的 config["store"]）
]

# 教学顺序：术语 → 最早允许出现的章号（与 LANGGRAPH_SCOPE 同源，此处用文档标题口径）
ORDER_RULES = [
    ("from langgraph", 4),
    ("StateGraph", 4),
    ("BaseChatModel", 16),
    ("bind_tools", 17),
    ("ToolNode", 18),
    ("create_react_agent", 19),
    ("checkpointer", 20),
    ("InMemoryStore", 21),
    ("interrupt(", 22),
    ("Subgraph", 23),
    ("stream_mode", 24),
    ("RetryPolicy", 25),
    ("StreamingResponse", 26),
]


def _seed(db) -> None:
    # 与 CLI 的初始化顺序一致：基础课内容 → 课程目录 → 题库 → 基础教材 → 阶段 4D
    seed_courses(db)
    seed_course_catalog(db)
    seed_questions(db)
    seed_textbook(db)
    seed_phase4d(db)


def _chapters(db, course_code: str = LG) -> list[Chapter]:
    course = db.scalars(select(Course).where(Course.code == course_code)).first()
    return sorted(course.chapters, key=lambda item: item.order_index)


def _lessons(db, course_code: str = LG) -> list[Lesson]:
    lessons: list[Lesson] = []
    for chapter in _chapters(db, course_code):
        lessons.extend(sorted(chapter.lessons, key=lambda item: item.order_index))
    return lessons


def _content_blob(content: CourseContent) -> str:
    return "\n".join(
        (getattr(content, field) or "") for field, _key, _label in CONTENT_MODULES
    )


# ---------------------------------------------------------------------------
# 一、课程章节完整
# ---------------------------------------------------------------------------


def test_chapter_and_lesson_structure(db_session):
    _seed(db_session)
    chapters = _chapters(db_session)
    assert len(chapters) == EXPECTED_CHAPTERS
    assert [item.order_index for item in chapters] == list(
        range(1, EXPECTED_CHAPTERS + 1)
    )

    lessons = _lessons(db_session)
    assert len(lessons) == EXPECTED_LESSONS
    for lesson in lessons:
        assert lesson.title and lesson.estimated_minutes
        assert lesson.difficulty in {"beginner", "intermediate", "advanced"}

    assert sum(len(chapter["lessons"]) for chapter in LG_CHAPTERS) == EXPECTED_LESSONS


def test_each_topic_owns_one_chapter(db_session):
    """需求列出的 28 个主题与 28 章逐条对应，顺序不得调整。"""
    _seed(db_session)
    assert len(TOPICS) == EXPECTED_CHAPTERS
    assert [item.title for item in _chapters(db_session)] == TOPICS


def test_teaching_order_is_respected(db_session):
    """概念 → 图基础 → 状态/节点/边 → 路由 → 模型 → 工具 → 持久化 → 审批 → 子图 → 流式 → 工程化。"""
    _seed(db_session)
    lessons = _lessons(db_session)

    # 1. 前 3 章只讲概念：一行业务框架代码都不能有
    for lesson in lessons:
        if lesson.chapter.order_index <= 3:
            code = lesson.content.example_code
            assert "langgraph" not in code, f"{lesson.code} 在概念章出现了框架代码"
            assert "StateGraph" not in code, f"{lesson.code} 提前用了 StateGraph"

    # 2. 术语不得提前出现
    for lesson in lessons:
        order = lesson.chapter.order_index
        blob = lesson.content.example_code + "\n" + lesson.content.syntax_explanation
        for term, intro in ORDER_RULES:
            if order < intro:
                assert term not in blob, (
                    f"{lesson.code}（第 {order} 章）提前使用了第 {intro} 章的 {term}"
                )

    # 3. 关键转折点的章号固定
    titles = {item.order_index: item.title for item in _chapters(db_session)}
    assert titles[4] == "LangGraph 项目初始化"
    assert titles[6] == "State"
    assert titles[16] == "接入大模型"
    assert titles[19] == "Agent 工作流"
    assert titles[20] == "Checkpointer"
    assert titles[28] == "综合项目：个人 AI 学习 Agent"


def test_key_points_covered(db_session):
    """9 个重点教学要求各有一章主课，且该章代码/语法里有关键落点。"""
    _seed(db_session)
    chapters = {item.order_index: item for item in _chapters(db_session)}
    for label, (order, title, markers) in KEY_POINTS.items():
        chapter = chapters[order]
        lesson_titles = [lesson.title for lesson in chapter.lessons]
        assert title in lesson_titles, f"{label} 没有对应课时《{title}》"
        blob = "\n".join(
            lesson.content.example_code + lesson.content.syntax_explanation
            for lesson in chapter.lessons
        )
        for marker in markers:
            assert marker in blob, (
                f"{label}（第 {order} 章 {chapter.title}）缺少关键片段 {marker}"
            )


def test_project_components_covered(db_session):
    """综合项目 6 项要求都能在 5 个课时里找到落点。"""
    _seed(db_session)
    project = [item for item in _chapters(db_session) if item.title.startswith("综合项目")]
    assert len(project) == 1 and project[0].order_index == EXPECTED_CHAPTERS
    lesson_titles = [lesson.title for lesson in project[0].lessons]
    assert len(lesson_titles) == 5

    by_title = {lesson.title: lesson.content for lesson in project[0].lessons}
    for requirement, (title, markers) in PROJECT_COMPONENTS.items():
        assert title in by_title, f"项目要求「{requirement}」没有对应课时"
        blob = _content_blob(by_title[title])
        for marker in markers:
            assert marker in blob, f"「{requirement}」在《{title}》里缺少 {marker}"

    assert all(
        lesson.content and lesson.content.example_code for lesson in project[0].lessons
    )


def test_project_does_not_execute_user_code(db_session):
    """不执行用户提交的代码：项目示例里没有 eval/exec/子进程，工具走白名单。"""
    _seed(db_session)
    project = [item for item in _chapters(db_session) if item.title.startswith("综合项目")][0]
    blob = "\n".join(_content_blob(lesson.content) for lesson in project.lessons)
    for danger in ("eval(", "exec(", "subprocess", "os.system", "__import__"):
        assert danger not in blob, f"综合项目里出现了不安全的 {danger}"
    assert "ALLOWED" in blob, "综合项目必须用 ALLOWED 白名单约束可调用工具"


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
        # 本课程的编辑标准比服务层更严：通俗解释 ≥80 字、逐行解释 ≥5 条
        assert len(content.plain_explanation.strip()) >= 80, (
            f"{lesson.code} 通俗解释只有 {len(content.plain_explanation.strip())} 字"
        )
        lines = [line for line in content.code_explanation.splitlines() if line.strip()]
        assert len(lines) >= 5, f"{lesson.code} 逐行解释只有 {len(lines)} 条"
        assert len(content.example_output.strip()) >= 80, f"{lesson.code} 示例输出过短"


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
        assert content[field], f"{field} 为空"


# ---------------------------------------------------------------------------
# 三、示例代码可用，版本口径统一
# ---------------------------------------------------------------------------


def test_example_code_is_valid_python(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        try:
            compile(lesson.content.example_code, lesson.code, "exec")
        except SyntaxError as exc:  # pragma: no cover - 失败时用于定位
            pytest.fail(f"{lesson.code} 示例代码语法错误：{exc}")


def test_version_facts_are_documented(db_session):
    """重要 API 标明版本，且把「旧写法已失效」写进教材。"""
    _seed(db_session)
    corpus = "\n".join(
        lesson.content.example_code + lesson.content.syntax_explanation
        + lesson.content.concept_explanation
        for lesson in _lessons(db_session)
    )
    for marker in VERSION_MARKERS:
        assert marker in corpus, f"教材没有写明版本事实：{marker}"

    # 每个重要 API 所在课时都要能说出「这是哪个版本的行为」
    by_title = {lesson.title: lesson.content for lesson in _lessons(db_session)}
    assert "1.2" in by_title["安装与版本确认"].syntax_explanation
    deprecated = by_title["工作流形态与版本定位"].syntax_explanation
    assert "弃用" in deprecated and "V2.0" in deprecated


def test_no_mixed_version_interfaces(db_session):
    """不混用版本接口：示例里不出现 V2 草案入口与已删除的旧参数。"""
    _seed(db_session)
    corpus = "\n".join(
        lesson.content.example_code for lesson in _lessons(db_session)
    )
    for forbidden in (
        "from langgraph.graph import StateGraphV2",
        'config["store"]',  # 早期教程写法，现取不到 store
        "ToolExecutor",  # 0.1 时代已被 ToolNode 取代
    ):
        assert forbidden not in corpus, f"示例里出现了不兼容的写法：{forbidden}"
    # create_react_agent 只在「历史形态」课时出现，且必须带弃用说明
    users = [
        lesson
        for lesson in _lessons(db_session)
        if "create_react_agent" in lesson.content.example_code
    ]
    assert users, "第 19 章应演示预制 Agent 的现状"
    for lesson in users:
        assert lesson.chapter.order_index == 19, f"{lesson.code} 不该出现预制 Agent"


def test_example_output_matches_real_execution():
    """示例输出不是手写的：逐节课真实执行 example_code，与教材 output 逐行比对。

    比对前做两处归一化——UUID 替换为占位符（第 20、28 章会打印随机线程 id）、
    教材里的 `#` 说明行剔除。这条测试保证「教材里贴的输出」和「代码真跑出来的输出」
    永远一致，防止改了代码忘了改文档。
    """
    uuid_pattern = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    def norm(text: str) -> str:
        text = uuid_pattern.sub("<uuid>", text)
        lines = [line.rstrip() for line in text.strip().splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines)

    def documented(lesson: dict) -> str:
        raw = lesson["output"].splitlines()
        if raw and raw[0].startswith("# 程序输出"):
            raw = raw[1:]
        kept = [line for line in raw if not line.strip().startswith("#")]
        return norm("\n".join(kept))

    problems: list[str] = []
    for chapter in LG_CHAPTERS:
        for lesson in chapter["lessons"]:
            buffer = io.StringIO()
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with redirect_stdout(buffer):
                        exec(
                            compile(lesson["example_code"], lesson["code"], "exec"),
                            {"__name__": "__main__"},
                        )
            except Exception as exc:  # noqa: BLE001 - 失败信息要原样带回
                problems.append(f"{lesson['code']} 运行异常 {type(exc).__name__}: {exc}")
                continue
            actual, expected = norm(buffer.getvalue()), documented(lesson)
            if actual != expected:
                problems.append(
                    f"{lesson['code']} 输出与教材不一致\n"
                    f"--- 实际 ---\n{actual}\n--- 教材 ---\n{expected}"
                )
    assert not problems, "\n\n".join(problems)


def test_no_late_terms_in_early_chapters(db_session):
    """与审计服务同一口径：示例代码与语法说明不得提前使用后面章节的术语。"""
    _seed(db_session)
    for lesson in _lessons(db_session):
        order = lesson.chapter.order_index
        blob = lesson.content.example_code + "\n" + lesson.content.syntax_explanation
        for term, intro_order in LANGGRAPH_SCOPE:
            if order < intro_order:
                assert term not in blob, (
                    f"{lesson.code} 第 {order} 章提前使用了第 {intro_order} 章的术语 {term}"
                )


# ---------------------------------------------------------------------------
# 四、练习与测验合规
# ---------------------------------------------------------------------------


def test_exercises_linked_to_lesson_knowledge_points(db_session):
    _seed(db_session)
    total = 0
    for lesson in _lessons(db_session):
        kp_ids = {kp.id for kp in lesson.knowledge_points}
        exercises = db_session.scalars(
            select(Exercise).where(Exercise.knowledge_point_id.in_(sorted(kp_ids)))
        ).all()
        assert len(exercises) >= 2, f"{lesson.code} 练习不足 2 道"
        total += len(exercises)
        for exercise in exercises:
            assert exercise.knowledge_point_id in kp_ids, (
                f"{exercise.code} 未挂在本课时知识点上"
            )
            assert exercise.reference_answer and exercise.explanation
    assert total == EXPECTED_EXERCISES


def test_question_distribution_and_types(db_session):
    _seed(db_session)
    type_counter: dict[str, int] = {}
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
            type_counter[question.question_type] = (
                type_counter.get(question.question_type, 0) + 1
            )
            categories[question.category] = categories.get(question.category, 0) + 1
            assert question.explanation, f"{question.code} 缺少解析"
        for category in ("基础理解", "代码阅读", "应用练习"):
            assert categories.get(category, 0) >= 2, (
                f"{lesson.code} 的{category}题不足 2 道"
            )
    assert total == EXPECTED_QUESTIONS
    assert set(type_counter) == {
        "single_choice",
        "multiple_choice",
        "true_false",
        "code_analysis",
        "code_writing",
        "short_answer",
    }


def test_question_difficulty_not_above_lesson(db_session):
    """难度不超课时一级：入门课时里不出现跨两级的题。"""
    _seed(db_session)
    rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
    for lesson in _lessons(db_session):
        lesson_rank = rank[lesson.difficulty]
        for kp in lesson.knowledge_points:
            for question in db_session.scalars(
                select(Question).where(Question.knowledge_point_id == kp.id)
            ).all():
                assert rank[question.difficulty] <= lesson_rank + 1, (
                    f"{question.code} 难度 {question.difficulty} 高于课时 {lesson.difficulty}"
                )


def test_knowledge_point_prerequisites_follow_course_order(db_session):
    _seed(db_session)
    lessons = _lessons(db_session)
    order = {
        kp.code: index for index, lesson in enumerate(lessons) for kp in lesson.knowledge_points
    }
    assert len(order) == EXPECTED_LESSONS

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

    resp = client.get(f"/api/v1/courses/{LG}/textbook")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapter_count"] == EXPECTED_CHAPTERS
    assert data["lesson_count"] == EXPECTED_LESSONS
    assert data["content_count"] == EXPECTED_LESSONS
    assert data["reviewed_count"] == EXPECTED_LESSONS

    audit = client.get(f"/api/v1/courses/{LG}/textbook/audit")
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

    resp = client.get(f"/api/v1/courses/{LG}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recommended_level"] == "L2"
    assert any(item["code"] == "ai-llm" for item in data["directions"])
    assert len(data["chapters"]) == EXPECTED_CHAPTERS
    assert META["level"] == "L2" and META["difficulty"] == "advanced"


# ---------------------------------------------------------------------------
# 六、依赖关系
# ---------------------------------------------------------------------------


def test_course_prerequisites(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == LG)).first()
    course_codes = {item.id: item.code for item in db_session.scalars(select(Course)).all()}
    prerequisites = {
        course_codes[edge.prerequisite_course_id]
        for edge in db_session.scalars(
            select(CoursePrerequisite).where(CoursePrerequisite.course_id == course.id)
        ).all()
    }
    assert prerequisites == {"python-advanced", "llm-api"}


def test_entry_knowledge_points_from_basics(db_session):
    _seed(db_session)
    course = db_session.scalars(select(Course).where(Course.code == LG)).first()
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
    stats = seed_phase4d(db_session)
    second = (
        db_session.scalar(select(func.count()).select_from(Lesson)),
        db_session.scalar(select(func.count()).select_from(CourseContent)),
        db_session.scalar(select(func.count()).select_from(Exercise)),
        db_session.scalar(select(func.count()).select_from(Question)),
    )
    assert first == second
    assert stats[LG]["contents_created"] == 0
    assert stats[LG]["exercises_created"] == 0
    assert stats[LG]["questions_created"] == 0
    assert stats["lessons_total"] == EXPECTED_LESSONS


def test_other_courses_untouched(db_session):
    _seed(db_session)
    assert len(_chapters(db_session, "python-basics")) == 20
    assert len(_lessons(db_session, "python-basics")) == 29
    assert len(_chapters(db_session, "python-advanced")) == 10
    assert len(_chapters(db_session, "python-database")) == 9
    assert len(_chapters(db_session, "fastapi-backend")) == 16
    assert len(_chapters(db_session, "llm-api")) == 16
    assert len(_chapters(db_session, "software-engineering-deploy")) == 8

    def snapshot() -> dict:
        return {
            code: (len(_chapters(db_session, code)), len(_lessons(db_session, code)))
            for code in (
                "python-basics",
                "python-advanced",
                "python-database",
                "fastapi-backend",
                "llm-api",
            )
        }

    before = snapshot()
    seed_phase4d(db_session)
    assert snapshot() == before


def test_lesson_knowledge_point_links(db_session):
    _seed(db_session)
    for lesson in _lessons(db_session):
        links = db_session.scalars(
            select(LessonKnowledgePoint).where(LessonKnowledgePoint.lesson_id == lesson.id)
        ).all()
        assert links, f"{lesson.code} 未关联知识点"
