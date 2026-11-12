"""V1.4 批次 5：Agent 真正产出业务卡片的定向测试。

覆盖：
- 卡片工厂只从真实 Service 返回的 Pydantic 业务对象取值；
- 每张卡片都通过 ``CARD_FIELD_RULES`` 自检，缺字段时宁可不发卡片；
- 未提交测验不泄露答案 / 解析 / 得分；错题卡片不泄露未作答复习题答案；
- 工具失败或暂不可用时不产卡；
- 真实 Agent 图（非 mock 注入）下发的 task_card 与业务接口数据一致，
  并持久化在同一条助手消息上。
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from app.agent.cards import (
    build_lesson_card,
    build_mistake_card,
    build_plan_card,
    build_plan_change_card,
    build_progress_card,
    build_quiz_card,
    build_quiz_result_card,
    build_task_card,
    cards_for_state,
)
from app.agent.contracts import (
    IntentResult,
    KnowledgePointSnapshot,
    LearningContext,
    ToolResult,
)
from app.schemas.cards import (
    CARD_FIELD_RULES,
    normalize_card,
    validate_card_payload,
)
from app.schemas.daily_task import DailyTaskKpOut, DailyTaskOut, TodayTasksOut
from app.schemas.learning_overview import (
    ChapterProgressOut,
    LearningOverviewOut,
)
from app.schemas.phase6 import PlanAdjustmentProposalOut
from app.schemas.plan import CurrentPlanOut, PlanItemOut, PlanVersionOut
from app.schemas.quiz import (
    MasteryUpdateOut,
    MistakeOut,
    QuestionOptionOut,
    QuizAttemptOut,
    QuizKnowledgePointOut,
    QuizQuestionOut,
)

KP = KnowledgePointSnapshot(
    code="py-var",
    name="变量",
    chapter_code="ch-1",
    chapter_title="Python 基础",
    learning_status="learning",
)


def _ok(data: object) -> ToolResult:
    return ToolResult(ok=True, status="ok", data=data)


def _intent(intent: str, sub_intent: str) -> IntentResult:
    return IntentResult(
        intent=intent, sub_intent=sub_intent, confidence=1.0, reason="测试"
    )


def _today_tasks(*, learning_goal: str = "理解变量的含义") -> TodayTasksOut:
    kp = DailyTaskKpOut.model_construct(
        code="py-var",
        name="变量",
        learning_goal=learning_goal,
        estimated_minutes=30,
        chapter_title="Python 基础",
    )
    task = DailyTaskOut.model_construct(
        id=uuid.uuid4(),
        status="pending",
        day_index=1,
        knowledge_point=kp,
        mastery_status="not_started",
    )
    return TodayTasksOut.model_construct(
        task_date=date(2026, 11, 9), generated=True, tasks=[task], note=None
    )


def _current_plan() -> CurrentPlanOut:
    item = PlanItemOut.model_construct(
        day_index=1,
        knowledge_point_name="变量",
        estimated_minutes=30,
        status="pending",
    )
    version = PlanVersionOut.model_construct(
        version_number=1,
        status="confirmed",
        learning_goal="掌握 Python 基础",
        daily_study_minutes=45,
        expected_duration_days=30,
        items=[item],
    )
    return CurrentPlanOut.model_construct(
        id=uuid.uuid4(),
        course_name="Python 零基础入门",
        current_version=version,
        pending_version=None,
    )


def _overview() -> LearningOverviewOut:
    return LearningOverviewOut.model_construct(
        plan_course_name="Python 零基础入门",
        mastered_count=3,
        learning_count=2,
        pending_verification_count=1,
        review_due_count=0,
        plan_progress_percent=42.5,
        chapters=[
            ChapterProgressOut.model_construct(
                chapter_title="Python 基础",
            )
        ],
    )


def _proposal() -> PlanAdjustmentProposalOut:
    return PlanAdjustmentProposalOut.model_construct(
        id=uuid.uuid4(),
        status="proposed",
        changes={"daily_study_minutes": 30},
        preview={
            "current": {"daily_study_minutes": 45},
            "proposed": {"daily_study_minutes": 30},
            "impacts": ["预计周期延长"],
        },
        reason="用户每天只有 30 分钟",
        requires_confirmation=True,
    )


def _question(*, submitted: bool = False) -> QuizQuestionOut:
    return QuizQuestionOut.model_construct(
        id=uuid.uuid4(),
        stem="下列哪个是合法的变量名？",
        question_type="single_choice",
        options=[
            QuestionOptionOut.model_construct(key="A", text="1var"),
            QuestionOptionOut.model_construct(key="B", text="var_1"),
        ],
        user_answer="A" if submitted else None,
        correct_answer="B" if submitted else None,
        explanation="变量名不能以数字开头" if submitted else None,
        score=0 if submitted else None,
        is_correct=False if submitted else None,
    )


def _attempt(*, submitted: bool = False) -> QuizAttemptOut:
    return QuizAttemptOut.model_construct(
        id=uuid.uuid4(),
        status="submitted" if submitted else "in_progress",
        scope_name="变量",
        total_points=10,
        score=8.0 if submitted else None,
        questions=[_question(submitted=submitted)],
        mastery_updates=[
            MasteryUpdateOut.model_construct(
                knowledge_point_name="变量",
                achieved=False,
                status_label="待验证",
            )
        ] if submitted else [],
    )


def _mistake() -> MistakeOut:
    return MistakeOut.model_construct(
        id=uuid.uuid4(),
        question=_question(),
        knowledge_point=QuizKnowledgePointOut.model_construct(name="变量"),
        last_answer="A",
        review_status="pending",
        attempt_count=1,
        next_review_at=None,
        pending_review_task_id=uuid.uuid4(),
    )


def _assert_valid(card: dict) -> None:
    assert card["card_version"] == "v1"
    assert card["type"] in CARD_FIELD_RULES
    assert validate_card_payload(card["type"], card["payload"]) is None
    # 批次 1 冻结的 normalize_card 只保留协议三字段，应原样通过。
    assert normalize_card(card) == card


# ---------------------------------------------------------------- 纯函数构造

def test_task_card_uses_real_today_task_fields() -> None:
    card = build_task_card(_today_tasks())
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["knowledge_point_code"] == "py-var"
    assert card["payload"]["estimated_minutes"] == 30
    assert card["payload"]["task_id"]


def test_incomplete_business_field_produces_no_card() -> None:
    # 学习目标为空字符串：字段表判定不合法，宁可不发卡片也不下发半成品。
    assert build_task_card(_today_tasks(learning_goal="  ")) is None


def test_non_business_object_produces_no_card() -> None:
    assert build_task_card({"tasks": []}) is None
    assert build_plan_card(None) is None
    assert build_progress_card("not-an-overview") is None
    assert build_quiz_card(None) is None


def test_plan_card_uses_effective_version() -> None:
    card = build_plan_card(_current_plan())
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["version_number"] == 1
    assert card["payload"]["items"][0]["knowledge_point_name"] == "变量"


def test_progress_card_numbers_come_from_backend() -> None:
    card = build_progress_card(_overview())
    assert card is not None
    _assert_valid(card)
    # 数字原值直传，不推算、不伪造。
    assert card["payload"]["mastered_count"] == 3
    assert card["payload"]["learning_count"] == 2
    assert card["payload"]["plan_progress_percent"] == 42.5


def test_plan_change_card_is_confirmation_only() -> None:
    card = build_plan_change_card(_proposal())
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["requires_confirmation"] is True
    assert card["payload"]["changes"] == {"daily_study_minutes": 30}


def test_quiz_card_never_exposes_answers() -> None:
    card = build_quiz_card(_attempt())
    assert card is not None
    _assert_valid(card)
    forbidden = {
        "correct_answer", "explanation", "score", "is_correct",
    }
    for question in card["payload"]["questions"]:
        assert not (set(question) & forbidden)
        assert question["options"][0] == {"key": "A", "text": "1var"}
    assert card["payload"]["attempt_id"]


def test_quiz_result_card_only_after_backend_grading() -> None:
    assert build_quiz_result_card(_attempt()) is None
    card = build_quiz_result_card(_attempt(submitted=True))
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["score"] == 8.0
    assert card["payload"]["questions"][0]["correct_answer"] == "B"


def test_mistake_card_carries_real_review_task_id() -> None:
    card = build_mistake_card([_mistake()])
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["review_task_id"]
    # 未作答复习题不剧透答案与解析。
    assert not ({"correct_answer", "explanation"} & set(card["payload"]))


def test_lesson_card_requires_learning_context() -> None:
    context = LearningContext.model_construct(
        today=date(2026, 11, 9), knowledge_point=KP
    )
    card = build_lesson_card(context, "变量是保存数据的名字。")
    assert card is not None
    _assert_valid(card)
    assert card["payload"]["knowledge_point_code"] == "py-var"
    assert build_lesson_card(None, "文本") is None
    assert build_lesson_card(context, "  ") is None


# ---------------------------------------------------------------- 状态分发

def test_cards_for_state_dispatches_by_intent() -> None:
    cases = [
        (
            _intent("planning", "today_tasks"),
            {"today_tasks": _ok(_today_tasks())},
            "task_card",
        ),
        (
            _intent("planning", "plan_overview"),
            {"plan": _ok(_current_plan())},
            "plan_card",
        ),
        (
            _intent("planning", "progress"),
            {"progress": _ok(_overview())},
            "progress_card",
        ),
        (
            _intent("planning", "adjust_plan"),
            {"adjust": _ok(_proposal())},
            "plan_change_card",
        ),
        (
            _intent("quiz", "generate_quiz"),
            {"quiz": _ok(_attempt())},
            "quiz_card",
        ),
        (
            _intent("review", "analyze_mistakes"),
            {"mistakes": _ok([_mistake()])},
            "mistake_card",
        ),
    ]
    for intent, results, expected in cases:
        cards = cards_for_state(
            intent=intent, tool_results=results, context=None, reply="回复"
        )
        assert [card["type"] for card in cards] == [expected], intent.sub_intent
        for card in cards:
            _assert_valid(card)


def test_failed_or_unavailable_tool_produces_no_card() -> None:
    for result in (
        ToolResult(ok=False, status="failed", data=_today_tasks()),
        ToolResult(ok=False, status="unavailable", data=None),
    ):
        cards = cards_for_state(
            intent=_intent("planning", "today_tasks"),
            tool_results={"today_tasks": result},
            context=None,
            reply="回复",
        )
        assert cards == []


def test_teaching_and_unsupported_intents() -> None:
    context = LearningContext.model_construct(
        today=date(2026, 11, 9), knowledge_point=KP
    )
    cards = cards_for_state(
        intent=_intent("teaching", "teach"),
        tool_results={},
        context=context,
        reply="变量是保存数据的名字。",
    )
    assert [card["type"] for card in cards] == ["lesson_card"]
    assert cards_for_state(
        intent=_intent("resource", "search_resources"),
        tool_results={},
        context=context,
        reply="资源列表",
    ) == []


# ---------------------------------------------------------------- 真实 Agent 集成

def _seed_courses(factory) -> None:
    from app.seed.course_seed import seed_courses

    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if name:
            events.append((name, data))
    return events


def test_real_agent_task_card_matches_business_api(api_env) -> None:
    """不经 mock 注入：真实主图产出的卡片与业务接口返回的任务是同一条数据。"""
    client, factory = api_env
    _seed_courses(factory)
    resp = client.put(
        "/api/v1/profile",
        json={
            "learning_goal": "三个月内掌握 Python 基础语法",
            "current_level": "L1",
            "daily_study_minutes": 45,
        },
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(
        "/api/v1/plans",
        json={
            "course_code": "python-basics",
            "learning_goal": "三个月内掌握 Python 基础语法",
            "current_level": "L1",
            "daily_study_minutes": 45,
            "expected_duration_days": 30,
        },
    )
    assert resp.status_code == 201, resp.text
    assert client.post(
        f"/api/v1/plans/{resp.json()['id']}/confirm"
    ).status_code == 200

    today = client.get("/api/v1/daily-tasks/today?generate=true")
    assert today.status_code == 200, today.text
    tasks = today.json()["tasks"]
    assert tasks
    task_ids = {task["id"] for task in tasks}
    kp_codes = {task["knowledge_point"]["code"] for task in tasks}

    conversation = client.post("/api/v1/conversations", json={})
    assert conversation.status_code == 201, conversation.text
    resp = client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages/stream",
        json={"content": "今天应该学什么？"},
    )
    assert resp.status_code == 200, resp.text
    cards = [data for name, data in _parse_sse(resp.text) if name == "card"]
    assert len(cards) == 1
    assert cards[0]["message_type"] == "task_card"
    payload = cards[0]["structured_data"]["payload"]
    assert payload["task_id"] in task_ids
    assert payload["knowledge_point_code"] in kp_codes
    assert validate_card_payload("task_card", payload) is None

    detail = client.get(
        f"/api/v1/conversations/{conversation.json()['id']}"
    ).json()
    assistant = detail["messages"][-1]
    assert assistant["message_type"] == "task_card"
    assert assistant["structured_data"]["cards"][0]["payload"]["task_id"] == (
        payload["task_id"]
    )
    assert assistant["status"] == "completed"
