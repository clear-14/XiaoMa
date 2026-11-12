"""V1.4 批次 8：两项产品裁决落地 + 只读成绩卡片的定向测试。

覆盖：
1. 超范围标记过滤器：跨增量剥离、正文不受污染、中途同名字样按普通文本处理；
2. 范围判定为超范围时不下发 lesson_card（在 ``cards_for_state`` 一处收口）；
3. ``quiz/quiz_result`` 只读意图：读最近一次已提交测验并产出结果卡片，
   未提交测验不产卡（答案隔离不破）；
4. 真实 Agent 图（stub 模型）端到端：流式内容与落库正文都不含标记，且不发卡片。
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

import httpx
from sqlalchemy import select

from app.agent.cards import cards_for_state
from app.agent.contracts import (
    IntentResult,
    KnowledgePointSnapshot,
    LearningContext,
    ToolResult,
)
from app.agent.intent import recognize_intent
from app.agent.scope_marker import MARKER, ScopeMarkerFilter
from app.agent.subgraphs.quiz import _compose_result
from app.models.course import KnowledgePoint
from app.schemas.quiz import (
    MasteryUpdateOut,
    QuestionOptionOut,
    QuizAttemptOut,
    QuizQuestionOut,
)
from app.seed.course_seed import seed_courses
from app.services import teaching_graph
from app.services.llm_client import LlmClient

KP_CODE = "python-basics-01-01"
KP_NAME = "什么是编程与 Python"
API_KEY = "sk-test-batch8-secret-key"

KP = KnowledgePointSnapshot(
    code="py-var",
    name="变量",
    chapter_code="ch-1",
    chapter_title="Python 基础",
    learning_status="learning",
)


# ---------------------------------------------------------------- 构造助手

def _intent(intent: str, sub_intent: str) -> IntentResult:
    return IntentResult(
        intent=intent, sub_intent=sub_intent, confidence=1.0, reason="测试"
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
        submitted_at=datetime(2026, 11, 9, 18, 20) if submitted else None,
        questions=[_question(submitted=submitted)],
        mastery_updates=(
            [
                MasteryUpdateOut.model_construct(
                    knowledge_point_name="变量",
                    achieved=False,
                    status_label="待验证",
                )
            ]
            if submitted
            else []
        ),
    )


def _capture() -> tuple[list[dict[str, str]], ScopeMarkerFilter]:
    events: list[dict[str, str]] = []
    return events, ScopeMarkerFilter(events.append)


# ---------------------------------------------------------------- 标记过滤器

def test_marker_across_chunks_is_stripped() -> None:
    events, scope = _capture()
    for chunk in ("[[out_of_", "scope]]", "\n\n", "列表不在本次", "知识点范围内。"):
        scope.feed(chunk)
    scope.flush()

    assert scope.out_of_scope is True
    assert scope.text == "列表不在本次知识点范围内。"
    assert "".join(event["delta"] for event in events) == scope.text
    assert MARKER not in "".join(event["delta"] for event in events)


def test_marker_with_body_in_one_chunk() -> None:
    events, scope = _capture()
    scope.feed(f"{MARKER}\n变量是保存数据的名字。")
    scope.flush()

    assert scope.out_of_scope is True
    assert scope.text == "变量是保存数据的名字。"
    assert [event["delta"] for event in events] == ["变量是保存数据的名字。"]


def test_plain_reply_is_forwarded_unchanged() -> None:
    events, scope = _capture()
    for chunk in ("变量是一个名字，", "用来指向内存里的数据。"):
        scope.feed(chunk)
    scope.flush()

    assert scope.out_of_scope is False
    assert scope.text == "变量是一个名字，用来指向内存里的数据。"
    assert "".join(event["delta"] for event in events) == scope.text


def test_marker_in_middle_is_plain_text() -> None:
    events, scope = _capture()
    scope.feed("列表")
    scope.feed(f"{MARKER}")
    scope.flush()

    # 判定在第一个增量就完成，后面的同名字样属于正文，不做语义猜测。
    assert scope.out_of_scope is False
    assert scope.text == f"列表{MARKER}"


def test_incomplete_marker_is_flushed_verbatim() -> None:
    events, scope = _capture()
    scope.feed("[[out")
    scope.flush()

    assert scope.out_of_scope is False
    assert scope.text == "[[out"
    assert "".join(event["delta"] for event in events) == "[[out"


def test_bracket_text_is_not_treated_as_marker() -> None:
    events, scope = _capture()
    scope.feed("[1] ")
    scope.feed("索引从 0 开始。")
    scope.flush()

    assert scope.out_of_scope is False
    assert scope.text == "[1] 索引从 0 开始。"
    assert "".join(event["delta"] for event in events) == scope.text


# ---------------------------------------------------------------- 发卡收口

def test_out_of_scope_suppresses_lesson_card() -> None:
    context = LearningContext.model_construct(
        today=date(2026, 11, 9), knowledge_point=KP
    )
    base = {
        "intent": _intent("teaching", "teach"),
        "tool_results": {},
        "context": context,
        "reply": "列表不在本次知识点范围内，我们先回到 print。",
    }
    # 默认（未标记）仍按讲解发卡，保持批次 5 行为不变。
    assert [
        card["type"] for card in cards_for_state(**base, reply_scope="")
    ] == ["lesson_card"]
    # 模型明确标记为超范围说明时不发讲解卡片。
    assert cards_for_state(**base, reply_scope="out_of_scope") == []


def test_quiz_result_card_requires_submitted_attempt() -> None:
    submitted = cards_for_state(
        intent=_intent("quiz", "quiz_result"),
        tool_results={
            "quiz_result": ToolResult(ok=True, status="ok", data=_attempt(submitted=True))
        },
        context=None,
        reply="最近一次测验：变量",
    )
    assert [card["type"] for card in submitted] == ["quiz_result_card"]
    payload = submitted[0]["payload"]
    assert payload["score"] == 8.0
    assert payload["questions"][0]["correct_answer"] == "B"

    # 未提交/未评分的结果不产卡：答案隔离与「只展示已评分结果」同时成立。
    in_progress = cards_for_state(
        intent=_intent("quiz", "quiz_result"),
        tool_results={
            "quiz_result": ToolResult(ok=True, status="ok", data=_attempt())
        },
        context=None,
        reply="还没有成绩",
    )
    assert in_progress == []

    # 工具暂不可用（还没有已提交测验）同样不产卡。
    assert (
        cards_for_state(
            intent=_intent("quiz", "quiz_result"),
            tool_results={
                "quiz_result": ToolResult(
                    ok=False, status="unavailable", message="还没有已提交的测验"
                )
            },
            context=None,
            reply="还没有成绩",
        )
        == []
    )


def test_recognize_intent_routes_quiz_result() -> None:
    cases = {
        "我上次测验成绩怎么样？": ("quiz", "quiz_result"),
        "我得了多少分": ("quiz", "quiz_result"),
        "查看我的测验记录": ("quiz", "quiz_history"),
        "给我出几道测验题": ("quiz", "generate_quiz"),
        # 「分数」在数学语境下另有含义，不能因为这个词就路由到测验。
        "讲讲分数和小数的区别": ("teaching", "teach"),
    }
    for message, expected in cases.items():
        intent = recognize_intent(message)
        assert (intent.intent, intent.sub_intent) == expected, message


def test_compose_result_uses_service_numbers() -> None:
    reply, status = _compose_result(
        ToolResult(ok=True, status="ok", data=_attempt(submitted=True))
    )
    assert status == "ok"
    assert "最近一次测验：「变量」" in reply
    assert "8 / 10 分" in reply
    assert "答对 0 题，答错 1 题" in reply
    assert "错题本" in reply

    reply, status = _compose_result(
        ToolResult(
            ok=False, status="unavailable", message="还没有已提交的测验，暂时没有成绩可以查看"
        )
    )
    assert status == "unavailable"
    assert "查看测验成绩未完成" in reply


# ---------------------------------------------------------------- 端到端

class _MarkerModelStub:
    """模拟 OpenAI 兼容流式服务，按给定分片返回（用于验证标记剥离）。"""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.requests: list[dict] = []

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        events = [
            {"choices": [{"delta": {"content": chunk}}]} for chunk in self.chunks
        ]
        payload = "".join(
            f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events
        ) + "data: [DONE]\n\n"
        return httpx.Response(
            200,
            content=payload.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    def install(self, monkeypatch) -> None:
        transport = httpx.MockTransport(self._handler)
        monkeypatch.setattr(
            teaching_graph,
            "create_llm_client",
            lambda request: LlmClient(request, transport=transport),
        )


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        name, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if name:
            events.append((name, data))
    return events


def _prepare(api_env) -> tuple[object, object]:
    client, factory = api_env
    db = factory()
    try:
        seed_courses(db)
    finally:
        db.close()
    assert client.put(
        "/api/v1/profile",
        json={
            "learning_goal": "转行做后端开发",
            "current_level": "L1",
            "daily_study_minutes": 45,
        },
    ).status_code == 200
    assert client.post(
        "/api/v1/model-configs",
        json={
            "name": "测试模型",
            "provider": "custom",
            "base_url": "https://llm.example/v1",
            "api_key": API_KEY,
            "model_name": "test-model",
            "temperature": 0.7,
            "max_tokens": 512,
            "timeout": 30,
            "is_default": True,
        },
    ).status_code == 201
    return client, factory


def test_out_of_scope_reply_has_no_card_and_no_marker(api_env, monkeypatch) -> None:
    client, factory = _prepare(api_env)
    db = factory()
    try:
        kp = db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.code == KP_CODE)
        ).one()
        # 会话必须绑定到真实知识点，超范围判定才有意义（否则本就没有讲解卡）。
        assert kp.name == KP_NAME
    finally:
        db.close()

    stub = _MarkerModelStub(
        ["[[out_of_", "scope]]\n\n", "列表不在本次知识点范围内，", "我们先回到 print。"]
    )
    stub.install(monkeypatch)

    conversation = client.post(
        "/api/v1/conversations", json={"knowledge_point_code": KP_CODE}
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["id"]

    resp = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "列表是什么？"},
    )
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    names = [name for name, _ in events]
    assert "card" not in names, names
    streamed = "".join(
        data["text"] for name, data in events if name == "delta"
    )
    assert MARKER not in streamed
    assert streamed.strip() == "列表不在本次知识点范围内，我们先回到 print。"

    detail = client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200, detail.text
    assistant = [
        message for message in detail.json()["messages"] if message["role"] == "assistant"
    ]
    assert len(assistant) == 1
    assert assistant[0]["content"].strip() == streamed.strip()
    assert MARKER not in assistant[0]["content"]
    assert assistant[0]["message_type"] == "text"
    assert assistant[0]["structured_data"] is None
