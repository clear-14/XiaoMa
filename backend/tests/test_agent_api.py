"""主 Agent（阶段 10）测试：意图路由、子图工具、异常与持久化。

覆盖用户验收场景：
1. 今天应该学什么？ → Planning / today_tasks
2. 解释 Python 变量。 → Teaching / 模型流式回复
3. 查看我的学习进度。 → Planning / progress（真实统计）
4. 为当前章节生成测验。 → Quiz / chapter
5. 分析我的错题。 → Review / analyze_mistakes
6. 调整我的学习计划。 → Planning / adjust_plan（只生成待确认草案）
7. 模型不可用/失败/超时 → 明确错误，不伪造成功；记录日志但不泄漏密钥
"""

import asyncio
import json

import httpx
from sqlalchemy import select

from app.agent.intent import recognize_intent
from app.models.course import KnowledgePoint
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.seed.course_seed import seed_courses
from app.seed.question_seed import seed_questions
from app.services import teaching_graph
from app.services.llm_client import LlmClient
from app.services.time_utils import utc_now_naive

KP_CODE = "python-basics-01-01"
KP_NAME = "什么是编程与 Python"
API_KEY = "sk-test-agent-secret-key"


# ---------------------------------------------------------------- 工具

def _seed(factory, *, questions: bool = False) -> None:
    db = factory()
    try:
        seed_courses(db)
        if questions:
            seed_questions(db)
    finally:
        db.close()


def _set_profile(client) -> None:
    resp = client.put(
        "/api/v1/profile",
        json={
            "learning_goal": "转行做后端开发",
            "current_level": "L1",
            "daily_study_minutes": 45,
        },
    )
    assert resp.status_code == 200, resp.text


def _create_default_model(client) -> None:
    resp = client.post(
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
    )
    assert resp.status_code == 201, resp.text


def _learn(factory, codes: list[str], status: str = "learning") -> None:
    db = factory()
    try:
        user = db.scalars(select(User).where(User.username == "local")).first()
        if user is None:
            user = User(username="local")
            db.add(user)
            db.flush()
        for code in codes:
            kp = db.scalars(
                select(KnowledgePoint).where(KnowledgePoint.code == code)
            ).one()
            db.add(
                LearningProfile(
                    user_id=user.id,
                    knowledge_point_id=kp.id,
                    status=status,
                    started_at=utc_now_naive(),
                )
            )
        db.commit()
    finally:
        db.close()


def _create_plan(client) -> str:
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
    plan_id = resp.json()["id"]
    resp = client.post(f"/api/v1/plans/{plan_id}/confirm")
    assert resp.status_code == 200, resp.text
    return plan_id


def _create_conversation(client, **payload) -> dict:
    resp = client.post("/api/v1/conversations", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _send(client, conversation_id: str, content: str):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": content},
    )


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        event, data = None, None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event:
            events.append((event, data))
    return events


def _reply_text(events: list[tuple[str, dict]]) -> str:
    return "".join(data["text"] for event, data in events if event == "delta")


def _conversation_messages(client, conversation_id: str) -> list[dict]:
    resp = client.get(f"/api/v1/conversations/{conversation_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["messages"]


class ChatModelStub:
    """模拟 OpenAI 兼容流式服务，记录请求。"""

    def __init__(self, chunks: list[str], *, error_after: int | None = None) -> None:
        self.chunks = chunks
        self.error_after = error_after
        self.requests: list[dict] = []

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        count = len(self.chunks) if self.error_after is None else self.error_after
        events = [
            {"choices": [{"delta": {"content": chunk}}]}
            for chunk in self.chunks[:count]
        ]
        if self.error_after is not None:
            events.append({"error": {"message": "upstream failed"}})
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


class SlowModelClient:
    """超时场景：模型迟迟不返回增量。"""

    async def stream(self, messages):
        await asyncio.sleep(1.0)
        yield "迟到的回复"


# ---------------------------------------------------------------- 意图识别

def test_recognize_intent_acceptance_scenarios():
    cases = {
        "今天应该学什么？": ("planning", "today_tasks"),
        "解释 Python 变量。": ("teaching", "teach"),
        "查看我的学习进度。": ("planning", "progress"),
        "为当前章节生成测验。": ("quiz", "generate_quiz"),
        "分析我的错题。": ("review", "analyze_mistakes"),
        "调整我的学习计划。": ("planning", "adjust_plan"),
        "我的学习计划是什么？": ("planning", "plan_overview"),
        "推荐 Python 变量的学习资料": ("resource", "search_resources"),
    }
    for message, expected in cases.items():
        intent = recognize_intent(message)
        assert (intent.intent, intent.sub_intent) == expected, message


# ---------------------------------------------------------------- 验收场景

def test_agent_plans_today_without_model_and_persists_history(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_plan(client)
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "今天应该学什么？")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    # V1.4 批次 5：Agent 从真实今日任务产出 task_card，事件序列新增 card。
    assert [event for event, _ in events] == ["start", "delta", "card", "done"]
    start = events[0][1]
    assert start["intent"] == "planning"
    assert start["sub_intent"] == "today_tasks"
    assert start["model"] is None  # 非教学子图不调用模型

    done = events[-1][1]
    assert done["subgraph"] == "planning"
    assert done["result_status"] == "ok"
    reply = _reply_text(events)
    assert "学习任务" in reply
    assert "第 1 天" in reply

    messages = _conversation_messages(client, conversation["id"])
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "今天应该学什么？"
    assert messages[1]["status"] == "completed"
    assert messages[1]["model_name"] is None
    assert messages[1]["content"] == reply

    # 卡片由后端业务结果生成，并与文本一起持久化在同一条助手消息上。
    card = events[2][1]
    assert card["card_version"] == "v1"
    assert card["message_type"] == "task_card"
    assert card["structured_data"]["payload"]["knowledge_point_code"]
    assert messages[1]["message_type"] == "task_card"
    assert messages[1]["structured_data"]["cards"][0]["type"] == "task_card"


def test_agent_teaching_streams_model_reply(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)
    stub = ChatModelStub(["变量是", "保存数据的名字。"])
    stub.install(monkeypatch)

    resp = _send(client, conversation["id"], "解释 Python 变量。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    # V1.4 批次 5：教学回复同时下发 lesson_card（知识点来自学习上下文）。
    assert [event for event, _ in events] == [
        "start", "delta", "delta", "card", "done",
    ]
    assert events[0][1]["intent"] == "teaching"
    assert events[0][1]["model"] == "test-model"
    assert _reply_text(events) == "变量是保存数据的名字。"
    assert events[-1][1]["subgraph"] == "teaching"

    # 教学提示词包含当前知识点，证明 Agent 读取了学习上下文
    system_prompt = stub.requests[0]["messages"][0]["content"]
    assert KP_NAME in system_prompt

    messages = _conversation_messages(client, conversation["id"])
    assert messages[-1]["status"] == "completed"
    assert messages[-1]["model_name"] == "test-model"
    assert messages[-1]["content"] == "变量是保存数据的名字。"

    card = events[3][1]
    assert card["message_type"] == "lesson_card"
    assert card["structured_data"]["payload"]["explanation"] == (
        "变量是保存数据的名字。"
    )
    assert messages[-1]["message_type"] == "lesson_card"
    assert messages[-1]["structured_data"]["cards"][0]["type"] == "lesson_card"


def test_agent_progress_uses_real_statistics(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _learn(factory, [KP_CODE], status="mastered")
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "查看我的学习进度。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert events[0][1]["intent"] == "planning"
    assert events[0][1]["sub_intent"] == "progress"
    reply = _reply_text(events)
    assert "学习进度概览" in reply
    assert "已学习知识点：1 个" in reply
    assert "已掌握 1" in reply
    assert "暂无（请先创建并确认学习计划）" in reply
    assert events[-1][1]["result_status"] == "ok"


def test_agent_generates_chapter_quiz_for_current_knowledge_point(api_env):
    client, factory = api_env
    _seed(factory, questions=True)
    _set_profile(client)
    _learn(factory, [KP_CODE])
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    resp = _send(client, conversation["id"], "为当前章节生成测验。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert events[0][1]["intent"] == "quiz"
    assert events[0][1]["sub_intent"] == "generate_quiz"
    reply = _reply_text(events)
    assert "生成一份测验" in reply
    assert "题量：3 题" in reply
    assert "测验中心" in reply
    assert events[-1][1]["result_status"] == "ok"

    # 子图必须调用真实 QuizService 生成可作答的测验记录
    attempts = client.get("/api/v1/quizzes")
    assert attempts.status_code == 200, attempts.text
    data = attempts.json()
    assert len(data) == 1
    assert data[0]["scope_type"] == "chapter"
    assert data[0]["question_count"] == 3


def _submit_all_wrong(client, attempt: dict) -> None:
    resp = client.post(
        f"/api/v1/quizzes/{attempt['id']}/submit",
        json={
            "answers": [
                {"question_id": question["id"], "answer": "wrong"}
                for question in attempt["questions"]
            ]
        },
    )
    assert resp.status_code == 200, resp.text


def test_agent_analyzes_mistakes_from_real_attempts(api_env):
    client, factory = api_env
    _seed(factory, questions=True)
    _set_profile(client)
    _learn(factory, [KP_CODE])

    created = client.post(
        "/api/v1/quizzes",
        json={"scope_type": "knowledge_point", "knowledge_point_code": KP_CODE},
    )
    assert created.status_code == 201, created.text
    _submit_all_wrong(client, created.json())

    conversation = _create_conversation(client)
    resp = _send(client, conversation["id"], "分析我的错题。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert events[0][1]["intent"] == "review"
    reply = _reply_text(events)
    assert "错题分析" in reply
    assert KP_NAME in reply
    assert "待复习 3 道" in reply
    assert "复习任务" in reply
    # 不剧透正确答案/解析
    assert "正确答案" not in reply
    assert events[-1][1]["result_status"] == "ok"


def test_agent_adjust_plan_creates_proposal_only(api_env):
    """阶段 6：Agent 只生成待确认提案，确认前不写任何计划版本。"""
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    plan_id = _create_plan(client)
    conversation = _create_conversation(client)

    resp = _send(
        client,
        conversation["id"],
        "调整我的学习计划，每天学习 30 分钟，期望 20 天完成。",
    )
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert events[0][1]["sub_intent"] == "adjust_plan"
    reply = _reply_text(events)
    assert "待确认方案" in reply
    assert "尚未保存" in reply

    # 确认前：计划完全没变，也没有待确认草案
    plan = client.get("/api/v1/plans/current")
    assert plan.status_code == 200, plan.text
    data = plan.json()
    assert data["id"] == plan_id
    assert data["current_version_number"] == 1
    assert data["pending_version_number"] is None
    assert data["current_version"]["daily_study_minutes"] == 45

    proposals = client.get("/api/v1/plan-adjustments/proposals").json()
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["status"] == "proposed"
    assert proposal["requires_confirmation"] is True
    assert proposal["changes"]["daily_study_minutes"] == 30
    assert proposal["changes"]["expected_duration_days"] == 20

    # 用户确认后才生成并生效新版本
    confirm = client.post(
        f"/api/v1/plan-adjustments/proposals/{proposal['id']}/confirm"
    )
    assert confirm.status_code == 200, confirm.text
    confirmed = client.get("/api/v1/plans/current").json()
    assert confirmed["current_version_number"] == 2
    assert confirmed["current_version"]["daily_study_minutes"] == 30
    assert confirmed["current_version"]["expected_duration_days"] == 20


def test_agent_adjust_plan_asks_for_parameters_without_changing_plan(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    plan_id = _create_plan(client)
    conversation = _create_conversation(client)

    resp = _send(client, conversation["id"], "调整我的学习计划。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)
    reply = _reply_text(events)

    assert "请告诉我" in reply
    assert "待确认提案" in reply
    assert "确认前不会保存" in reply
    plan = client.get("/api/v1/plans/current")
    assert plan.status_code == 200, plan.text
    data = plan.json()
    assert data["pending_version_number"] is None
    assert data["current_version_number"] == 1


# ---------------------------------------------------------------- 异常处理

def test_agent_teaching_without_model_returns_explicit_409(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    resp = _send(client, conversation["id"], "解释 Python 变量。")
    assert resp.status_code == 409
    assert "尚未配置默认模型" in resp.json()["detail"]
    # 在流式开始前失败，不保存本轮用户消息
    assert _conversation_messages(client, conversation["id"]) == []


def test_agent_model_failure_saves_error_and_hides_api_key(api_env, monkeypatch, caplog):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)
    stub = ChatModelStub(["部分"], error_after=1)
    stub.install(monkeypatch)

    with caplog.at_level("DEBUG"):
        resp = _send(client, conversation["id"], "解释 Python 变量。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert [event for event, _ in events] == ["start", "delta", "error"]
    assert events[-1][1]["message"]
    messages = _conversation_messages(client, conversation["id"])
    assert messages[-1]["status"] == "error"
    assert messages[-1]["content"] == "部分"
    assert messages[-1]["error_message"]
    assert API_KEY not in caplog.text


def test_agent_tool_failure_is_reported_not_faked(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_plan(client)
    conversation = _create_conversation(client)

    from app.services.daily_task_service import DailyTaskService

    def _boom(self):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(DailyTaskService, "get_today_tasks", _boom)

    resp = _send(client, conversation["id"], "今天应该学什么？")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert [event for event, _ in events] == ["start", "error"]
    assert "服务暂时不可用" in events[-1][1]["message"]
    messages = _conversation_messages(client, conversation["id"])
    assert messages[-1]["status"] == "error"
    assert messages[-1]["content"] == ""


def test_agent_timeout_returns_error_instead_of_waiting(api_env, monkeypatch):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    _create_default_model(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)
    monkeypatch.setattr(
        teaching_graph, "create_llm_client", lambda request: SlowModelClient()
    )
    monkeypatch.setenv("XIAOMA_AGENT_TIMEOUT_SECONDS", "0.1")
    from app.core.config import get_settings

    get_settings.cache_clear()

    resp = _send(client, conversation["id"], "解释 Python 变量。")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)

    assert [event for event, _ in events] == ["start", "error"]
    assert "超时" in events[-1][1]["message"]
    messages = _conversation_messages(client, conversation["id"])
    assert messages[-1]["status"] == "error"
    assert "超时" in messages[-1]["error_message"]


def test_agent_resource_search_returns_registered_resources(api_env):
    client, factory = api_env
    _seed(factory)
    _set_profile(client)
    conversation = _create_conversation(client, knowledge_point_code=KP_CODE)

    resp = _send(client, conversation["id"], "推荐 Python 变量的学习资料")
    assert resp.status_code == 200, resp.text
    events = _parse_sse(resp.text)
    reply = _reply_text(events)

    assert events[0][1]["intent"] == "resource"
    assert "学习资源" in reply
    assert "docs.python.org" in reply
    # “变量”应排在第 1 章泛 Python 资源之前（相关度排序）。
    assert reply.index("变量与赋值") < reply.index("什么是编程与 Python")
    assert events[-1][1]["result_status"] == "ok"
